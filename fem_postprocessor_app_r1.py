import streamlit as st
import meshio
import numpy as np
import tempfile
import os
import re
from pathlib import Path
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MOOSE Exodus Viewer", layout="wide", page_icon="🦌")

# -----------------------------------------------------------------------------
# Helper Functions - File Discovery (split-file aware)
# -----------------------------------------------------------------------------
def is_part_file(filename):
    """Return True if filename ends with .part followed by digits."""
    return bool(re.search(r'\.part\d+$', filename))

def get_base_name_from_part(part_filename):
    """Remove the .partN suffix to get the base filename."""
    return re.sub(r'\.part\d+$', '', part_filename)

def get_file_size_mb(file_path):
    """Get file size in MB with error handling."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0

def find_exodus_files_grouped(search_dir):
    """
    Recursively find all Exodus files and split-file groups in the given directory.
    Returns a list of groups, each a dict with keys:
        display_name : str  – user‑friendly name (includes part count and total size)
        base_name    : str  – base filename (e.g., 'solidtwo.e')
        directory    : str  – directory containing the files
        part_files   : list – sorted list of part file paths (empty for single file)
        single_file  : str or None – path if not split
        total_size_mb: float – sum of file sizes in MB
    """
    exodus_extensions = ['.e', '.exo', '.exodus', '.out', '.ex2']
    regular_files = []
    part_files = []

    if not os.path.exists(search_dir):
        return []

    for root, dirs, files in os.walk(search_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file.startswith('.'):
                continue
            full_path = os.path.join(root, file)
            if is_part_file(file):
                part_files.append(full_path)
            else:
                ext = os.path.splitext(file)[1].lower()
                if ext in exodus_extensions:
                    regular_files.append(full_path)

    # Group part files by (directory, base_name)
    part_groups = {}
    for pf in part_files:
        dirname = os.path.dirname(pf)
        base = get_base_name_from_part(os.path.basename(pf))
        key = (dirname, base)
        part_groups.setdefault(key, []).append(pf)

    # Sort part files numerically within each group
    for key in part_groups:
        part_groups[key].sort(key=lambda x: int(re.search(r'\.part(\d+)$', x).group(1)))

    # Build groups from part files
    groups = []
    for (dirname, base), part_list in part_groups.items():
        total_size = sum(get_file_size_mb(p) for p in part_list)
        display_path = os.path.join(dirname, base) if dirname != '.' else base
        groups.append({
            'display_name': f"{display_path} ({len(part_list)} parts, {total_size:.1f} MB)",
            'base_name': base,
            'directory': dirname,
            'part_files': part_list,
            'single_file': None,
            'total_size_mb': total_size
        })

    # Add regular files that are NOT already represented by a part group
    bases_with_parts = {(dirname, base) for (dirname, base) in part_groups.keys()}
    for rf in regular_files:
        dirname = os.path.dirname(rf)
        basename = os.path.basename(rf)
        if (dirname, basename) not in bases_with_parts:
            size_mb = get_file_size_mb(rf)
            display_path = os.path.join(dirname, basename) if dirname != '.' else basename
            groups.append({
                'display_name': display_path,
                'base_name': basename,
                'directory': dirname,
                'part_files': [],
                'single_file': rf,
                'total_size_mb': size_mb
            })

    # Sort groups alphabetically by display name
    groups.sort(key=lambda g: g['display_name'].lower())
    return groups

def combine_parts(part_files, output_path):
    """
    Concatenate part files (in order) into a single output file.
    Returns True on success, False on failure.
    """
    try:
        with open(output_path, 'wb') as outfile:
            for part in part_files:
                with open(part, 'rb') as infile:
                    outfile.write(infile.read())
        return True
    except Exception as e:
        st.error(f"Failed to combine parts: {e}")
        return False

# -----------------------------------------------------------------------------
# Helper Functions - Mesh Loading
# -----------------------------------------------------------------------------
def load_exodus_data(file_path):
    """
    Reads an Exodus file using meshio.
    Returns meshio mesh object or None on error.
    """
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        return None

    try:
        with st.spinner(f"Reading {os.path.basename(file_path)}..."):
            mesh = meshio.read(file_path)
            return mesh
    except ImportError as e:
        st.error(f"Missing dependency: {e}")
        st.info("Try: `pip install netCDF4 h5py` or use conda: `conda install -c conda-forge seacas`")
        return None
    except Exception as e:
        st.error(f"Error reading file: {type(e).__name__}: {e}")
        st.info("Ensure the file is a valid MOOSE Exodus output file.")
        return None

# -----------------------------------------------------------------------------
# Helper Functions - Surface Extraction for Plotly
# -----------------------------------------------------------------------------
def extract_mesh_surfaces(meshio_mesh):
    """
    Extract surface triangles from mesh for Plotly visualization.
    Works with tetrahedra, hexahedra, triangles, quads, wedges, and pyramids.

    Returns:
        tuple: (points, faces, face_centers) or (None, None, None) on failure
    """
    if meshio_mesh is None:
        return None, None, None

    points = meshio_mesh.points

    if points is None or len(points) == 0:
        return None, None, None

    # Collect all faces from cells
    faces = []

    # Check if cells exist
    if not meshio_mesh.cells or len(meshio_mesh.cells) == 0:
        st.warning("No cell data found in mesh. Cannot extract surfaces.")
        return None, None, None

    for cell_block in meshio_mesh.cells:
        if cell_block is None:
            continue

        cell_type = cell_block.type
        cells = cell_block.data

        if cells is None or len(cells) == 0:
            continue

        try:
            if cell_type in ['tetra', 'tetrahedron']:
                # Each tetrahedron has 4 triangular faces
                for cell in cells:
                    if len(cell) >= 4:
                        tetra_faces = [
                            [cell[0], cell[1], cell[2]],
                            [cell[0], cell[1], cell[3]],
                            [cell[0], cell[2], cell[3]],
                            [cell[1], cell[2], cell[3]]
                        ]
                        faces.extend(tetra_faces)

            elif cell_type in ['hexahedron', 'hex', 'hexa']:
                # Each hexahedron has 6 quadrilateral faces
                for cell in cells:
                    if len(cell) >= 8:
                        hex_faces = [
                            [cell[0], cell[1], cell[2], cell[3]], # bottom
                            [cell[4], cell[5], cell[6], cell[7]], # top
                            [cell[0], cell[1], cell[5], cell[4]], # front
                            [cell[2], cell[3], cell[7], cell[6]], # back
                            [cell[0], cell[3], cell[7], cell[4]], # left
                            [cell[1], cell[2], cell[6], cell[5]]  # right
                        ]
                        for quad in hex_faces:
                            faces.append([quad[0], quad[1], quad[2]])
                            faces.append([quad[0], quad[2], quad[3]])

            elif cell_type in ['triangle', 'tri']:
                for cell in cells:
                    if len(cell) >= 3:
                        faces.append([cell[0], cell[1], cell[2]])

            elif cell_type in ['quad', 'quadrilateral', 'quad8', 'quad9']:
                for cell in cells:
                    if len(cell) >= 4:
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[0], cell[2], cell[3]])

            elif cell_type in ['wedge', 'triangular_prism']:
                for cell in cells:
                    if len(cell) >= 6:
                        # Triangle faces
                        faces.append([cell[0], cell[1], cell[2]]) # bottom
                        faces.append([cell[3], cell[5], cell[4]]) # top (reversed for normal)
                        # Quad faces split into triangles
                        faces.append([cell[0], cell[1], cell[4]])
                        faces.append([cell[0], cell[4], cell[3]])
                        faces.append([cell[1], cell[2], cell[5]])
                        faces.append([cell[1], cell[5], cell[4]])
                        faces.append([cell[2], cell[0], cell[3]])
                        faces.append([cell[2], cell[3], cell[5]])

            elif cell_type in ['pyramid', 'pyra']:
                for cell in cells:
                    if len(cell) >= 5:
                        # Quad base split into 2 triangles
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[0], cell[2], cell[3]])
                        # Triangle sides
                        faces.append([cell[0], cell[1], cell[4]])
                        faces.append([cell[1], cell[2], cell[4]])
                        faces.append([cell[2], cell[3], cell[4]])
                        faces.append([cell[3], cell[0], cell[4]])

            elif cell_type in ['line', 'line2', 'line3']:
                # Skip 1D elements for 3D visualization
                continue

            else:
                # Unknown cell type - skip with warning (only once)
                if not hasattr(extract_mesh_surfaces, '_warned_types'):
                    extract_mesh_surfaces._warned_types = set()
                if cell_type not in extract_mesh_surfaces._warned_types:
                    extract_mesh_surfaces._warned_types.add(cell_type)
                    st.warning(f"Skipping unsupported cell type: {cell_type}")

        except (IndexError, TypeError, ValueError) as e:
            st.warning(f"Error processing {cell_type} cells: {e}")
            continue

    if len(faces) == 0:
        st.warning("No valid faces extracted from mesh. Check cell types in your Exodus file.")
        return None, None, None

    try:
        faces = np.array(faces, dtype=np.int32)

        # Validate faces array
        if faces.ndim != 2 or faces.shape[1] != 3:
            st.error(f"Invalid faces array shape: {faces.shape}")
            return None, None, None

        # Calculate face centers for scalar interpolation
        face_centers = np.mean(points[faces], axis=1)

        return points, faces, face_centers

    except Exception as e:
        st.error(f"Error converting faces to array: {e}")
        return None, None, None

# -----------------------------------------------------------------------------
# Helper Functions - Plotly Visualization
# -----------------------------------------------------------------------------
def create_plotly_mesh(points, faces, values=None, color_map='Viridis',
                       opacity=0.9, show_edges=False, title="Mesh",
                       show_scalar_bar=True):
    """
    Create a Plotly 3D mesh visualization.
    """
    if points is None or faces is None:
        fig = go.Figure()
        fig.add_annotation(
            text="⚠️ No mesh data available for visualization",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            scene=dict(
                xaxis_title='X', yaxis_title='Y', zaxis_title='Z',
                aspectmode='data'
            ),
            height=600,
            title=title
        )
        return fig

    if len(points) == 0 or len(faces) == 0:
        return create_plotly_mesh(None, None, None, title=title)

    try:
        i = faces[:, 0]
        j = faces[:, 1]
        k = faces[:, 2]
    except IndexError:
        st.error("Invalid faces array format")
        return create_plotly_mesh(None, None, None, title=title)

    intensity = None
    colorscale = None
    showscale = False
    colorbar = None

    if values is not None and len(values) > 0:
        try:
            values = np.asarray(values).flatten()
            if len(values) == len(faces):
                intensity = values
                colorscale = color_map
                showscale = show_scalar_bar
                if show_scalar_bar:
                    colorbar = dict(
                        title=dict(text=title, font=dict(size=12)),
                        thickness=20,
                        len=0.5
                    )
            else:
                st.warning(f"Value count ({len(values)}) doesn't match face count ({len(faces)}). Showing geometry only.")
        except Exception as e:
            st.warning(f"Could not apply scalar values: {e}")

    mesh_trace = go.Mesh3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        i=i,
        j=j,
        k=k,
        intensity=intensity,
        colorscale=colorscale,
        opacity=opacity,
        showscale=showscale,
        colorbar=colorbar,
        flatshading=True,
        lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.5, specular=0.2),
        lightposition=dict(x=100, y=100, z=100),
        name='Mesh'
    )

    fig = go.Figure(data=[mesh_trace])

    # Add edge lines if requested and mesh is not too large
    if show_edges and len(faces) < 50000:
        edge_x = []
        edge_y = []
        edge_z = []

        for face in faces:
            for idx1, idx2 in [(0, 1), (1, 2), (2, 0)]:
                try:
                    p1 = points[face[idx1]]
                    p2 = points[face[idx2]]
                    edge_x.extend([p1[0], p2[0], None])
                    edge_y.extend([p1[1], p2[1], None])
                    edge_z.extend([p1[2], p2[2], None])
                except (IndexError, TypeError):
                    continue

        if len(edge_x) > 0:
            fig.add_trace(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='black', width=0.5),
                name='Edges',
                opacity=0.6,
                showlegend=False
            ))

    fig.update_layout(
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='white'
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=18)),
        hovermode='closest',
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    return fig

# -----------------------------------------------------------------------------
# Helper Functions - Format Conversion for ParaView
# -----------------------------------------------------------------------------
def convert_to_vtu(meshio_mesh, output_path):
    if meshio_mesh is None:
        return False
    try:
        meshio.write(output_path, meshio_mesh, file_format="vtu")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except ImportError as e:
        if 'h5py' in str(e).lower():
            st.error("VTU export requires h5py. Install with: pip install h5py")
        else:
            st.error(f"VTU export error: {e}")
        return False
    except Exception as e:
        st.error(f"VTU conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_vtp(meshio_mesh, output_path):
    if meshio_mesh is None:
        return False
    try:
        points, faces, _ = extract_mesh_surfaces(meshio_mesh)
        if points is None or faces is None:
            st.warning("Could not extract surface for VTP export")
            return False
        triangle_cells = meshio.CellBlock('triangle', faces)
        surface_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
        if hasattr(meshio_mesh, 'point_data') and meshio_mesh.point_data:
            surface_mesh.point_data = meshio_mesh.point_data
        meshio.write(output_path, surface_mesh, file_format="vtp")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        st.error(f"VTP conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_vtk(meshio_mesh, output_path):
    if meshio_mesh is None:
        return False
    try:
        meshio.write(output_path, meshio_mesh, file_format="vtk")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        st.error(f"VTK conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_xdmf(meshio_mesh, output_path):
    if meshio_mesh is None:
        return False
    try:
        import h5py
        meshio.write(output_path, meshio_mesh, file_format="xdmf")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except ImportError:
        return False
    except Exception as e:
        st.error(f"XDMF conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_stl(meshio_mesh, output_path):
    if meshio_mesh is None:
        return False
    try:
        points, faces, _ = extract_mesh_surfaces(meshio_mesh)
        if points is None or faces is None:
            return False
        triangle_cells = meshio.CellBlock('triangle', faces)
        surface_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
        meshio.write(output_path, surface_mesh, file_format="stl")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        st.error(f"STL conversion error: {type(e).__name__}: {e}")
        return False

# -----------------------------------------------------------------------------
# Helper Functions - Data Processing
# -----------------------------------------------------------------------------
def get_variable_values(meshio_mesh, variable_name, faces):
    if variable_name is None or faces is None:
        return None

    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}

    if variable_name in point_data:
        point_values = point_data[variable_name]
        if point_values is None:
            return None
        point_values = np.asarray(point_values)
        if point_values.ndim > 1 and point_values.shape[1] > 1:
            point_values = np.linalg.norm(point_values, axis=1)
        try:
            face_values = np.mean(point_values[faces], axis=1)
            return face_values
        except (IndexError, TypeError) as e:
            st.warning(f"Could not interpolate point data: {e}")
            return None

    elif variable_name in cell_data:
        cell_values = cell_data[variable_name]
        if cell_values is None:
            return None
        if isinstance(cell_values, list):
            arrays = [np.asarray(arr) for arr in cell_values if arr is not None]
            if len(arrays) == 0:
                return None
            cell_values = np.concatenate(arrays)
        else:
            cell_values = np.asarray(cell_values)
        if cell_values.ndim > 1 and cell_values.shape[1] > 1:
            cell_values = np.linalg.norm(cell_values, axis=1)
        total_cells = sum(len(block.data) for block in meshio_mesh.cells if block.data is not None)
        if total_cells == 0:
            return None
        total_faces = len(faces)
        if total_faces == 0:
            return None

        # Simplified mapping (repeat cell values for its faces)
        if len(cell_values) == total_cells:
            face_values = np.zeros(total_faces)
            face_idx = 0
            for cell_block in meshio_mesh.cells:
                if cell_block.data is None:
                    continue
                n_block_cells = len(cell_block.data)
                if cell_block.type in ['tetra', 'tetrahedron']:
                    faces_per_this_cell = 4
                elif cell_block.type in ['hexahedron', 'hex', 'hexa']:
                    faces_per_this_cell = 12
                elif cell_block.type in ['triangle', 'tri']:
                    faces_per_this_cell = 1
                elif cell_block.type in ['quad', 'quadrilateral']:
                    faces_per_this_cell = 2
                else:
                    faces_per_this_cell = 4
                for cell_idx in range(n_block_cells):
                    if face_idx + faces_per_this_cell <= total_faces:
                        face_values[face_idx:face_idx+faces_per_this_cell] = cell_values[
                            sum(len(cb.data) for cb in meshio_mesh.cells if cb.data is not None and cb != cell_block) + cell_idx
                        ]
                        face_idx += faces_per_this_cell
            return face_values if np.any(face_values) else None

        if len(cell_values) == total_faces:
            return cell_values
        return None

    return None

def get_available_variables(meshio_mesh):
    if meshio_mesh is None:
        return [], [], []
    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
    point_vars = [v for v in point_data.keys() if v and isinstance(v, str)]
    cell_vars = [v for v in cell_data.keys() if v and isinstance(v, str)]
    all_vars = point_vars + cell_vars
    return point_vars, cell_vars, all_vars

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    st.title("🦌 MOOSE Exodus Output Viewer")
    st.markdown("""
    **Upload** a MOOSE simulation output file (`.exodus`, `.e`, `.exo`) to visualize results interactively.
    Files from the `dataset` folder are automatically detected; split files (`.e.part1`, `.e.part2`, …) are combined on the fly.
    **Download** in ParaView‑compatible formats (.vtu, .vtp, .vtk, .stl).
    """)

    app_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(app_dir, "dataset")

    # Session state
    if 'selected_group' not in st.session_state:
        st.session_state.selected_group = None
    if 'combined_file_path' not in st.session_state:
        st.session_state.combined_file_path = None
    if 'meshio_mesh' not in st.session_state:
        st.session_state.meshio_mesh = None
    if 'cache_dir' not in st.session_state:
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="moose_viewer_")
    if 'last_error' not in st.session_state:
        st.session_state.last_error = None

    # Clean up previous combined file
    if st.session_state.combined_file_path and os.path.exists(st.session_state.combined_file_path):
        try:
            os.remove(st.session_state.combined_file_path)
        except:
            pass
        st.session_state.combined_file_path = None

    # Sidebar
    with st.sidebar:
        st.header("1. Select File Source")
        exodus_groups = find_exodus_files_grouped(dataset_dir)

        source_option = st.radio(
            "Choose file source:",
            ["Dataset Folder", "Upload File"],
            key="source_radio",
            horizontal=False
        )

        selected_group = None
        if source_option == "Dataset Folder":
            st.subheader("Dataset Files")
            if exodus_groups:
                st.success(f"✅ Found {len(exodus_groups)} Exodus file(s)/group(s) in `dataset/`")
                display_names = [g['display_name'] for g in exodus_groups]
                selected_display = st.selectbox(
                    "Select Exodus File / Split Group",
                    display_names,
                    key="file_select",
                    index=0
                )
                selected_group = next(g for g in exodus_groups if g['display_name'] == selected_display)

                if selected_group['part_files']:
                    st.info(f"📁 **Split group:** {selected_group['base_name']}\n"
                            f"📊 **Total size:** {selected_group['total_size_mb']:.2f} MB\n"
                            f"🧩 **Parts:** {len(selected_group['part_files'])}")
                else:
                    st.info(f"📁 **File:** {selected_group['single_file']}\n"
                            f"📊 **Size:** {selected_group['total_size_mb']:.2f} MB")
            else:
                st.warning(f"⚠️ No Exodus files found in `dataset/` folder.")
                st.markdown(f"**Expected path:** `{dataset_dir}`")
        else:
            st.subheader("Upload File")
            uploaded_file = st.file_uploader(
                "Choose an Exodus file",
                type=['e', 'exodus', 'exo', 'out', 'ex2'],
                key="file_uploader",
                accept_multiple_files=False
            )
            if uploaded_file is not None:
                tmp_filename = f"uploaded_{uploaded_file.name}"
                tmp_path = os.path.join(st.session_state.cache_dir, tmp_filename)
                try:
                    with open(tmp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    selected_group = {
                        'display_name': uploaded_file.name,
                        'base_name': uploaded_file.name,
                        'directory': st.session_state.cache_dir,
                        'part_files': [],
                        'single_file': tmp_path,
                        'total_size_mb': len(uploaded_file.getvalue()) / (1024 * 1024)
                    }
                    st.info(f"📊 **Uploaded:** {uploaded_file.name}\n\n📦 **Size:** {selected_group['total_size_mb']:.2f} MB")
                except Exception as e:
                    st.error(f"Error saving uploaded file: {e}")

        st.divider()
        st.header("2. Visualization Settings")
        color_map = st.selectbox("Color Map", ["Viridis","Plasma","Inferno","Magma","Cividis",
                                                "Jet","Rainbow","Portland","Blackbody","Earth",
                                                "Ice","Turbo","Spectral"], index=0)
        opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05)
        show_edges = st.checkbox("Show Mesh Edges", value=False)
        show_scalar_bar = st.checkbox("Show Color Bar", value=True)

        st.divider()
        st.header("ℹ️ About")
        st.markdown("""
        **MOOSE Exodus Viewer**  
        - Built with Streamlit + Plotly + Meshio  
        - ParaView‑compatible exports  
        - Automatic split‑file reassembly  
        """)

    # Main content
    if selected_group is not None:
        # Determine actual file path to load
        if selected_group['part_files']:
            combined_name = f"combined_{selected_group['base_name']}_{os.urandom(4).hex()}.e"
            combined_path = os.path.join(st.session_state.cache_dir, combined_name)
            if combine_parts(selected_group['part_files'], combined_path):
                load_path = combined_path
                st.session_state.combined_file_path = combined_path
            else:
                st.error("Failed to combine split files. Cannot load mesh.")
                load_path = None
        else:
            load_path = selected_group['single_file']
            st.session_state.combined_file_path = None

        # Reload mesh if needed
        if load_path and (st.session_state.selected_group != selected_group or st.session_state.meshio_mesh is None):
            st.session_state.selected_group = selected_group
            st.session_state.meshio_mesh = None
            st.session_state.last_error = None

            meshio_mesh = load_exodus_data(load_path)
            if meshio_mesh is not None:
                st.session_state.meshio_mesh = meshio_mesh
                st.rerun()
            else:
                st.session_state.last_error = "Failed to load mesh"
        else:
            meshio_mesh = st.session_state.meshio_mesh

        # Display mesh if loaded
        if meshio_mesh is not None:
            points, faces, face_centers = extract_mesh_surfaces(meshio_mesh)
            point_vars, cell_vars, all_vars = get_available_variables(meshio_mesh)

            col1, col2, col3 = st.columns([3,1,1])
            with col1:
                if not all_vars:
                    st.info("ℹ️ No data variables found. Visualizing geometry only.")
                    variable_name = None
                else:
                    variable_name = st.selectbox("📊 Select Variable to Plot", all_vars, index=0)
            with col2:
                st.metric("🔵 Points", f"{len(meshio_mesh.points):,}" if meshio_mesh.points is not None else "0")
            with col3:
                n_cells = sum(len(c.data) for c in meshio_mesh.cells if c.data is not None) if meshio_mesh.cells else 0
                st.metric("🔷 Cells", f"{n_cells:,}")

            values = None
            if variable_name and faces is not None and len(faces) > 0:
                values = get_variable_values(meshio_mesh, variable_name, faces)

            if points is not None and faces is not None and len(points) > 0 and len(faces) > 0:
                fig = create_plotly_mesh(
                    points, faces, values,
                    color_map=color_map,
                    opacity=opacity,
                    show_edges=show_edges,
                    title=variable_name if variable_name else "Mesh Geometry",
                    show_scalar_bar=show_scalar_bar
                )
                st.divider()
                st.subheader("🎨 3D Visualization")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ Could not extract mesh surfaces for visualization.")

            # Download section
            st.divider()
            st.subheader("📥 Download for ParaView")
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)

            with col_d1:
                vtu_filename = "mesh_output.vtu"
                vtu_path = os.path.join(st.session_state.cache_dir, vtu_filename)
                vtu_success = convert_to_vtu(meshio_mesh, vtu_path)
                if vtu_success and os.path.exists(vtu_path):
                    with open(vtu_path, 'rb') as f:
                        file_bytes = f.read()
                    st.download_button(
                        label="📥 Download .VTU",
                        data=file_bytes,
                        file_name=vtu_filename,
                        mime="application/xml",
                        key="download_vtu",
                        help="Unstructured Grid format (recommended for ParaView)"
                    )
                else:
                    st.button("❌ VTU Unavailable", disabled=True, key="download_vtu_disabled",
                              help="Requires h5py: pip install h5py")

            with col_d2:
                vtp_filename = "mesh_surface.vtp"
                vtp_path = os.path.join(st.session_state.cache_dir, vtp_filename)
                vtp_success = convert_to_vtp(meshio_mesh, vtp_path)
                if vtp_success and os.path.exists(vtp_path):
                    with open(vtp_path, 'rb') as f:
                        file_bytes = f.read()
                    st.download_button(
                        label="📥 Download .VTP",
                        data=file_bytes,
                        file_name=vtp_filename,
                        mime="application/xml",
                        key="download_vtp",
                        help="PolyData format (surface mesh only)"
                    )
                else:
                    st.button("❌ VTP Unavailable", disabled=True, key="download_vtp_disabled")

            with col_d3:
                vtk_filename = "mesh_output.vtk"
                vtk_path = os.path.join(st.session_state.cache_dir, vtk_filename)
                vtk_success = convert_to_vtk(meshio_mesh, vtk_path)
                if vtk_success and os.path.exists(vtk_path):
                    with open(vtk_path, 'rb') as f:
                        file_bytes = f.read()
                    st.download_button(
                        label="📥 Download .VTK",
                        data=file_bytes,
                        file_name=vtk_filename,
                        mime="text/plain",
                        key="download_vtk",
                        help="Legacy VTK format (widely compatible)"
                    )
                else:
                    st.button("❌ VTK Unavailable", disabled=True, key="download_vtk_disabled")

            with col_d4:
                stl_filename = "mesh_surface.stl"
                stl_path = os.path.join(st.session_state.cache_dir, stl_filename)
                stl_success = convert_to_stl(meshio_mesh, stl_path)
                if stl_success and os.path.exists(stl_path):
                    with open(stl_path, 'rb') as f:
                        file_bytes = f.read()
                    st.download_button(
                        label="📥 Download .STL",
                        data=file_bytes,
                        file_name=stl_filename,
                        mime="application/sla",
                        key="download_stl",
                        help="STL format (for CAD/3D printing)"
                    )
                else:
                    st.button("❌ STL Unavailable", disabled=True, key="download_stl_disabled")

            col_xdmf1, col_xdmf2 = st.columns([1, 3])
            with col_xdmf1:
                xdmf_filename = "mesh_output.xdmf"
                xdmf_path = os.path.join(st.session_state.cache_dir, xdmf_filename)
                xdmf_success = convert_to_xdmf(meshio_mesh, xdmf_path)
                if xdmf_success and os.path.exists(xdmf_path):
                    with open(xdmf_path, 'rb') as f:
                        file_bytes = f.read()
                    st.download_button(
                        label="📥 Download .XDMF",
                        data=file_bytes,
                        file_name=xdmf_filename,
                        mime="application/xml",
                        key="download_xdmf",
                        help="XDMF format (requires h5py, for large datasets)"
                    )
                else:
                    st.button("❌ XDMF Unavailable", disabled=True, key="download_xdmf_disabled",
                              help="Requires h5py: pip install h5py")

            with col_xdmf2:
                st.info("""
                **💡 ParaView Instructions:**
                1. Download any format above (.vtu recommended for full mesh)
                2. Open ParaView → File → Open → Select downloaded file
                3. Click "Apply" in Properties panel
                4. Use "Color By" dropdown to select variables
                5. Use "Rescale to Data Range" for proper color mapping
                """)
        else:
            st.error("❌ Failed to load mesh data. Please check the file format and try again.")
            if st.session_state.last_error:
                st.code(st.session_state.last_error)
    else:
        st.info("👈 Please select or upload an Exodus file from the sidebar to begin.")

    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>🦌 MOOSE Exodus Viewer v2.0 | Built with Streamlit + Plotly + Meshio | Split‑file support</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
