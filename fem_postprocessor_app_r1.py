import streamlit as st
import meshio
import numpy as np
import tempfile
import os
import sys
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import base64
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MOOSE Exodus Viewer", layout="wide", page_icon="🦌")

# -----------------------------------------------------------------------------
# Helper Functions - File Discovery
# -----------------------------------------------------------------------------
def find_exodus_files(search_dir):
    """
    Recursively find all Exodus files in the given directory.
    Returns a list of file paths.
    """
    exodus_extensions = ['.e', '.exo', '.exodus', '.out', '.ex2']
    exodus_files = []
    
    if not os.path.exists(search_dir):
        return exodus_files
    
    try:
        for root, dirs, files in os.walk(search_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                # Skip hidden files
                if file.startswith('.'):
                    continue
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in exodus_extensions:
                    full_path = os.path.join(root, file)
                    exodus_files.append(full_path)
    except PermissionError:
        st.warning(f"Permission denied accessing directory: {search_dir}")
    
    # Sort files alphabetically by name
    exodus_files.sort(key=lambda x: os.path.basename(x).lower())
    return exodus_files

def get_file_display_name(file_path, base_dir):
    """Creates a user-friendly display name for the file."""
    try:
        rel_path = os.path.relpath(file_path, base_dir)
        return rel_path
    except ValueError:
        # On Windows, if paths are on different drives
        return os.path.basename(file_path)
    except Exception:
        return os.path.basename(file_path)

def get_file_size_mb(file_path):
    """Get file size in MB with error handling."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0

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
                        # Faces: (0,1,2), (0,1,3), (0,2,3), (1,2,3)
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
                        # Faces of hexahedron (standard VTK ordering)
                        hex_faces = [
                            [cell[0], cell[1], cell[2], cell[3]],  # bottom
                            [cell[4], cell[5], cell[6], cell[7]],  # top
                            [cell[0], cell[1], cell[5], cell[4]],  # front
                            [cell[2], cell[3], cell[7], cell[6]],  # back
                            [cell[0], cell[3], cell[7], cell[4]],  # left
                            [cell[1], cell[2], cell[6], cell[5]]   # right
                        ]
                        for quad in hex_faces:
                            # Split quad into 2 triangles
                            faces.append([quad[0], quad[1], quad[2]])
                            faces.append([quad[0], quad[2], quad[3]])
            
            elif cell_type in ['triangle', 'tri']:
                for cell in cells:
                    if len(cell) >= 3:
                        faces.append([cell[0], cell[1], cell[2]])
            
            elif cell_type in ['quad', 'quadrilateral', 'quad8', 'quad9']:
                for cell in cells:
                    if len(cell) >= 4:
                        # Split quad into 2 triangles
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[0], cell[2], cell[3]])
            
            elif cell_type in ['wedge', 'triangular_prism']:
                for cell in cells:
                    if len(cell) >= 6:
                        # Wedge: 2 triangles + 3 quads
                        # Triangle faces
                        faces.append([cell[0], cell[1], cell[2]])  # bottom
                        faces.append([cell[3], cell[5], cell[4]])  # top (reversed for normal)
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
                        # Pyramid: 1 quad base + 4 triangles
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
    
    Args:
        points: numpy array of shape (n_points, 3)
        faces: numpy array of shape (n_faces, 3) with vertex indices
        values: optional array of scalar values for coloring
        color_map: Plotly colorscale name
        opacity: mesh opacity (0.0 to 1.0)
        show_edges: whether to draw mesh edges
        title: title for the visualization
        show_scalar_bar: whether to show the colorbar
    
    Returns:
        plotly.graph_objects.Figure
    """
    if points is None or faces is None:
        # Return empty figure with message
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
    
    # Validate inputs
    if len(points) == 0 or len(faces) == 0:
        return create_plotly_mesh(None, None, None, title=title)
    
    # Extract triangle vertex indices
    try:
        i = faces[:, 0]
        j = faces[:, 1]
        k = faces[:, 2]
    except IndexError:
        st.error("Invalid faces array format")
        return create_plotly_mesh(None, None, None, title=title)
    
    # Prepare values for coloring
    intensity = None
    colorscale = None
    showscale = False
    colorbar = None
    
    if values is not None and len(values) > 0:
        try:
            # Ensure values is 1D and matches number of faces
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
    
    # Create mesh3d trace
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
    
    # Update layout
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
    """
    Convert meshio mesh to VTU format (ParaView compatible).
    Returns True on success, False on failure.
    """
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
    """
    Convert meshio mesh to VTP format (PolyData, ParaView compatible).
    Returns True on success, False on failure.
    """
    if meshio_mesh is None:
        return False
    try:
        # Extract surface for VTP (PolyData format)
        points, faces, _ = extract_mesh_surfaces(meshio_mesh)
        if points is None or faces is None:
            st.warning("Could not extract surface for VTP export")
            return False
        
        # Create new mesh with triangle cells only
        triangle_cells = meshio.CellBlock('triangle', faces)
        surface_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
        
        # Copy point data if available
        if hasattr(meshio_mesh, 'point_data') and meshio_mesh.point_data:
            surface_mesh.point_data = meshio_mesh.point_data
        
        meshio.write(output_path, surface_mesh, file_format="vtp")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        st.error(f"VTP conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_vtk(meshio_mesh, output_path):
    """
    Convert meshio mesh to legacy VTK format.
    Returns True on success, False on failure.
    """
    if meshio_mesh is None:
        return False
    try:
        meshio.write(output_path, meshio_mesh, file_format="vtk")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        st.error(f"VTK conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_xdmf(meshio_mesh, output_path):
    """
    Convert meshio mesh to XDMF format (ParaView compatible).
    Note: Requires h5py package.
    Returns True on success, False on failure.
    """
    if meshio_mesh is None:
        return False
    try:
        # Try to import h5py for XDMF support
        import h5py
        meshio.write(output_path, meshio_mesh, file_format="xdmf")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except ImportError:
        # h5py not available - return False silently, UI will handle
        return False
    except Exception as e:
        st.error(f"XDMF conversion error: {type(e).__name__}: {e}")
        return False

def convert_to_stl(meshio_mesh, output_path):
    """
    Convert mesh surface to STL format (widely compatible).
    Returns True on success, False on failure.
    """
    if meshio_mesh is None:
        return False
    try:
        # Extract surface triangles
        points, faces, _ = extract_mesh_surfaces(meshio_mesh)
        if points is None or faces is None:
            return False
        
        # Create surface mesh
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
    """
    Extract scalar values for a variable, interpolated to face centers.
    
    Returns:
        numpy array of values or None
    """
    if variable_name is None or faces is None:
        return None
    
    # Get point and cell data dictionaries safely
    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
    
    # Check if variable exists in point data
    if variable_name in point_data:
        point_values = point_data[variable_name]
        if point_values is None:
            return None
        
        # Convert to numpy array if needed
        point_values = np.asarray(point_values)
        
        # Handle vector data - compute magnitude
        if point_values.ndim > 1 and point_values.shape[1] > 1:
            point_values = np.linalg.norm(point_values, axis=1)
        
        # Interpolate to face centers by averaging vertex values
        try:
            face_values = np.mean(point_values[faces], axis=1)
            return face_values
        except (IndexError, TypeError) as e:
            st.warning(f"Could not interpolate point data: {e}")
            return None
    
    # Check if variable exists in cell data
    elif variable_name in cell_data:
        cell_values = cell_data[variable_name]
        if cell_values is None:
            return None
        
        # cell_data can be a list of arrays (one per cell block) or single array
        if isinstance(cell_values, list):
            # Concatenate arrays from different cell blocks
            arrays = [np.asarray(arr) for arr in cell_values if arr is not None]
            if len(arrays) == 0:
                return None
            cell_values = np.concatenate(arrays)
        else:
            cell_values = np.asarray(cell_values)
        
        # Handle vector cell data
        if cell_values.ndim > 1 and cell_values.shape[1] > 1:
            cell_values = np.linalg.norm(cell_values, axis=1)
        
        # Map cell values to faces
        # Count cells to determine faces per cell ratio
        total_cells = sum(len(block.data) for block in meshio_mesh.cells if block.data is not None)
        if total_cells == 0:
            return None
        
        total_faces = len(faces)
        if total_faces == 0:
            return None
        
        # Simple approach: repeat each cell value for its faces
        # This assumes uniform face distribution (approximation)
        faces_per_cell = total_faces / total_cells
        
        # Create mapping: for each face, find which cell it belongs to
        # Simplified: just repeat values proportionally
        if len(cell_values) == total_cells:
            # Expand cell values to face count
            face_values = np.zeros(total_faces)
            face_idx = 0
            for cell_block in meshio_mesh.cells:
                if cell_block.data is None:
                    continue
                n_block_cells = len(cell_block.data)
                # Estimate faces per cell for this block type
                if cell_block.type in ['tetra', 'tetrahedron']:
                    faces_per_this_cell = 4
                elif cell_block.type in ['hexahedron', 'hex', 'hexa']:
                    faces_per_this_cell = 12  # 6 quads * 2 triangles each
                elif cell_block.type in ['triangle', 'tri']:
                    faces_per_this_cell = 1
                elif cell_block.type in ['quad', 'quadrilateral']:
                    faces_per_this_cell = 2
                else:
                    faces_per_this_cell = 4  # default
                
                for cell_idx in range(n_block_cells):
                    if face_idx + faces_per_this_cell <= total_faces:
                        face_values[face_idx:face_idx+faces_per_this_cell] = cell_values[
                            sum(len(cb.data) for cb in meshio_mesh.cells if cb.data is not None and cb != cell_block) + cell_idx
                        ]
                        face_idx += faces_per_this_cell
            
            return face_values if np.any(face_values) else None
        
        # Fallback: if lengths match directly
        if len(cell_values) == total_faces:
            return cell_values
        
        return None
    
    return None

def get_available_variables(meshio_mesh):
    """
    Get list of available point and cell variables.
    
    Returns:
        tuple: (point_vars, cell_vars, all_vars)
    """
    if meshio_mesh is None:
        return [], [], []
    
    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
    
    point_vars = list(point_data.keys()) if point_data else []
    cell_vars = list(cell_data.keys()) if cell_data else []
    
    # Filter out None keys and empty names
    point_vars = [v for v in point_vars if v and isinstance(v, str)]
    cell_vars = [v for v in cell_vars if v and isinstance(v, str)]
    
    all_vars = point_vars + cell_vars
    
    return point_vars, cell_vars, all_vars

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    """Main application entry point."""
    
    st.title("🦌 MOOSE Exodus Output Viewer")
    st.markdown("""
    **Upload** a MOOSE simulation output file (`.exodus`, `.e`, `.exo`) to visualize results interactively.
    Files from the `dataset` folder are automatically detected. 
    **Download** in ParaView-compatible formats (.vtu, .vtp, .vtk, .stl).
    """)
    
    # Get the directory where app.py is located
    app_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(app_dir, "dataset")
    
    # Initialize session state for caching
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None
    if 'meshio_mesh' not in st.session_state:
        st.session_state.meshio_mesh = None
    if 'cache_dir' not in st.session_state:
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="moose_viewer_")
    if 'last_error' not in st.session_state:
        st.session_state.last_error = None
    
    # Sidebar - File Selection
    with st.sidebar:
        st.header("1. Select File Source")
        
        # Find Exodus files in dataset folder
        exodus_files = find_exodus_files(dataset_dir)
        
        source_option = st.radio(
            "Choose file source:",
            ["Dataset Folder", "Upload File"],
            key="source_radio",
            horizontal=False
        )
        
        selected_file_path = None
        
        if source_option == "Dataset Folder":
            st.subheader("Dataset Files")
            if exodus_files:
                st.success(f"✅ Found {len(exodus_files)} Exodus file(s) in `dataset/`")
                
                # Create display names for dropdown
                file_options = {}
                for f in exodus_files:
                    display_name = get_file_display_name(f, app_dir)
                    file_options[display_name] = f
                
                selected_display = st.selectbox(
                    "Select Exodus File",
                    list(file_options.keys()),
                    key="file_select",
                    index=0 if len(file_options) == 1 else 0
                )
                selected_file_path = file_options[selected_display]
                
                # Show file info
                file_size = get_file_size_mb(selected_file_path)
                st.info(f"📁 **Path:** `{selected_file_path}`\n\n📊 **Size:** {file_size:.2f} MB")
            else:
                st.warning(f"⚠️ No Exodus files found in `dataset/` folder.")
                st.markdown(f"""
                **Expected path:** `{dataset_dir}`
                
                **Supported extensions:** `.e`, `.exo`, `.exodus`, `.out`, `.ex2`
                
                **Tip:** Create the `dataset` folder next to `app.py` and add your Exodus files.
                """)
        else:
            st.subheader("Upload File")
            uploaded_file = st.file_uploader(
                "Choose an Exodus file",
                type=['e', 'exodus', 'exo', 'out', 'ex2'],
                key="file_uploader",
                accept_multiple_files=False
            )
            if uploaded_file is not None:
                # Create temporary file in cache directory
                tmp_filename = f"uploaded_{uploaded_file.name}"
                tmp_path = os.path.join(st.session_state.cache_dir, tmp_filename)
                try:
                    with open(tmp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    selected_file_path = tmp_path
                    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
                    st.info(f"📊 **Uploaded:** {uploaded_file.name}\n\n📦 **Size:** {file_size:.2f} MB")
                except Exception as e:
                    st.error(f"Error saving uploaded file: {e}")
                    selected_file_path = None
        
        st.divider()
        st.header("2. Visualization Settings")
        
        color_map = st.selectbox(
            "Color Map",
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", 
             "Jet", "Rainbow", "Portland", "Blackbody", "Earth",
             "Ice", "Turbo", "Spectral"],
            index=0,
            key="colormap_select"
        )
        opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05, key="opacity_slider")
        show_edges = st.checkbox("Show Mesh Edges", value=False, key="edges_checkbox")
        show_scalar_bar = st.checkbox("Show Color Bar", value=True, key="scalarbar_checkbox")
        
        st.divider()
        st.header("ℹ️ About")
        st.markdown("""
        **MOOSE Exodus Viewer**
        
        - Built with Streamlit + Plotly + Meshio
        - ParaView-compatible exports
        - No PyVista/VTK compilation required
        
        **Supported Formats:**
        - Input: `.e`, `.exo`, `.exodus`
        - Output: `.vtu`, `.vtp`, `.vtk`, `.stl`
        """)
    
    # Main Content - File Processing
    if selected_file_path is not None:
        # Check if we need to reload the mesh
        needs_reload = (
            st.session_state.selected_file_path != selected_file_path or 
            st.session_state.meshio_mesh is None
        )
        
        if needs_reload:
            st.session_state.selected_file_path = selected_file_path
            st.session_state.meshio_mesh = None
            st.session_state.last_error = None
            
            # Load Data
            meshio_mesh = load_exodus_data(selected_file_path)
            
            if meshio_mesh is not None:
                st.session_state.meshio_mesh = meshio_mesh
                # Use fragment to rerun without full reload
                try:
                    st.rerun()
                except AttributeError:
                    # Fallback for older Streamlit versions
                    st.experimental_rerun()
            else:
                st.session_state.last_error = "Failed to load mesh"
        else:
            meshio_mesh = st.session_state.meshio_mesh
        
        # Display mesh if loaded successfully
        if meshio_mesh is not None:
            # Extract surface for visualization
            points, faces, face_centers = extract_mesh_surfaces(meshio_mesh)
            
            # Get available variables
            point_vars, cell_vars, all_vars = get_available_variables(meshio_mesh)
            
            # Variable selection UI
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                if not all_vars:
                    st.info("ℹ️ No data variables found in mesh. Visualizing geometry only.")
                    variable_name = None
                else:
                    variable_name = st.selectbox(
                        "📊 Select Variable to Plot",
                        all_vars,
                        key="var_select",
                        index=0
                    )
            
            with col2:
                n_points = len(meshio_mesh.points) if meshio_mesh.points is not None else 0
                st.metric("🔵 Points", f"{n_points:,}")
            
            with col3:
                n_cells = sum(len(c.data) for c in meshio_mesh.cells if c.data is not None) if meshio_mesh.cells else 0
                st.metric("🔷 Cells", f"{n_cells:,}")
            
            # Get values for selected variable
            values = None
            if variable_name and faces is not None and len(faces) > 0:
                values = get_variable_values(meshio_mesh, variable_name, faces)
            
            # Create and display Plotly visualization
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
                st.plotly_chart(fig, use_container_width=True, key="plotly_viz")
            else:
                st.warning("⚠️ Could not extract mesh surfaces for visualization.")
                st.markdown("""
                **Possible causes:**
                - Mesh contains unsupported cell types
                - File is corrupted or incomplete
                - Mesh is 1D or 2D only
                
                **Try:** Download the file and open in ParaView for full support.
                """)
            
            # Download Section
            st.divider()
            st.subheader("📥 Download for ParaView")
            
            # Mesh info expander
            with st.expander("📋 Mesh & Data Information", expanded=False):
                st.write(f"**File:** `{os.path.basename(selected_file_path)}`")
                st.write(f"**Full Path:** `{selected_file_path}`")
                st.write(f"**Points:** {len(meshio_mesh.points) if meshio_mesh.points is not None else 0:,}")
                st.write(f"**Cells:** {sum(len(c.data) for c in meshio_mesh.cells if c.data is not None):,}")
                
                cell_types = [c.type for c in meshio_mesh.cells if c.type is not None]
                if cell_types:
                    st.write(f"**Cell Types:** {', '.join(set(cell_types))}")
                
                if point_vars:
                    st.write("**📍 Point Variables:**")
                    for var in point_vars:
                        try:
                            data = meshio_mesh.point_data[var]
                            if data is not None:
                                data = np.asarray(data)
                                st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
                        except Exception:
                            st.write(f"  - `{var}`: <could not read>")
                
                if cell_vars:
                    st.write("**🔷 Cell Variables:**")
                    for var in cell_vars:
                        try:
                            data = meshio_mesh.cell_data[var]
                            if data is not None:
                                if isinstance(data, list):
                                    shapes = [np.asarray(d).shape for d in data if d is not None]
                                    st.write(f"  - `{var}`: {len(data)} blocks, shapes={shapes}")
                                else:
                                    data = np.asarray(data)
                                    st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
                        except Exception:
                            st.write(f"  - `{var}`: <could not read>")
            
            # Download buttons grid
            st.markdown("### Available Formats")
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            
            # VTU Download (Unstructured Grid - recommended)
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
                    st.button(
                        label="❌ VTU Unavailable",
                        disabled=True,
                        key="download_vtu_disabled",
                        help="Requires h5py: pip install h5py"
                    )
            
            # VTP Download (PolyData - surface only)
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
                    st.button(
                        label="❌ VTP Unavailable",
                        disabled=True,
                        key="download_vtp_disabled"
                    )
            
            # VTK Download (Legacy format)
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
                    st.button(
                        label="❌ VTK Unavailable",
                        disabled=True,
                        key="download_vtk_disabled"
                    )
            
            # STL Download (CAD/3D printing)
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
                    st.button(
                        label="❌ STL Unavailable",
                        disabled=True,
                        key="download_stl_disabled"
                    )
            
            # XDMF Download (separate row, requires h5py)
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
                    st.button(
                        label="❌ XDMF Unavailable",
                        disabled=True,
                        key="download_xdmf_disabled",
                        help="Requires h5py: pip install h5py"
                    )
            
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
            # Mesh loading failed
            st.error("❌ Failed to load mesh data. Please check the file format and try again.")
            if st.session_state.last_error:
                st.code(st.session_state.last_error)
            
    else:
        # No file selected
        st.info("👈 Please select or upload an Exodus file from the sidebar to begin.")
        
        # Demo/Help section
        with st.expander("📖 Don't have a file? See expected format", expanded=False):
            st.code("""
# MOOSE input file snippet to ensure Exodus output
[Outputs]
  exodus = true
  file_base = my_simulation
[]

# To output specific variables:
[Outputs/exodus]
  output_on = 'timestep_end'
[]

# Example variables to output:
[AuxKernels]
  [./temperature]
    variable = temp
    [./]
  []
[]
            """, language="python")
            
            st.markdown("""
            ### 📁 Expected Folder Structure
            ```
            your_project/
            ├── app.py                    # This Streamlit app
            ├── requirements.txt          # Python dependencies
            └── dataset/                  # Folder for Exodus files
                ├── two_phase_output.e
                ├── simulation_1.e
                └── results/
                    └── case_study.exo
            ```
            
            ### 🔧 Troubleshooting
            | Issue | Solution |
            |-------|----------|
            | "No module named netCDF4" | `pip install netCDF4` |
            | "No module named h5py" | `pip install h5py` (for VTU/XDMF) |
            | File not found | Check `dataset/` folder exists next to `app.py` |
            | Empty visualization | Try downloading and opening in ParaView |
            | Slow loading | Large meshes may take time; use surface formats (.vtp, .stl) |
            """)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>
        🦌 MOOSE Exodus Viewer v2.0 | 
        Built with Streamlit + Plotly + Meshio | 
        ParaView Compatible Downloads
        </small>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Application Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
