import streamlit as st
import meshio
import numpy as np
import tempfile
import os
import sys
import re
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
# Helper Functions - File Discovery (updated for split files)
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
# Helper Functions - Mesh Loading (unchanged except for error handling)
# -----------------------------------------------------------------------------
def load_exodus_data(file_path):
    """Read an Exodus file using meshio. Returns meshio mesh object or None."""
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
# Helper Functions - Surface Extraction (unchanged)
# -----------------------------------------------------------------------------
def extract_mesh_surfaces(meshio_mesh):
    # ... (keep original code) ...
    # (not repeated here for brevity; same as in original)
    pass

# -----------------------------------------------------------------------------
# Helper Functions - Plotly Visualization (unchanged)
# -----------------------------------------------------------------------------
def create_plotly_mesh(points, faces, values=None, color_map='Viridis',
                       opacity=0.9, show_edges=False, title="Mesh",
                       show_scalar_bar=True):
    # ... (keep original code) ...
    pass

# -----------------------------------------------------------------------------
# Helper Functions - Format Conversion (unchanged)
# -----------------------------------------------------------------------------
def convert_to_vtu(meshio_mesh, output_path):
    # ... (keep original code) ...
    pass

def convert_to_vtp(meshio_mesh, output_path):
    # ... (keep original code) ...
    pass

def convert_to_vtk(meshio_mesh, output_path):
    # ... (keep original code) ...
    pass

def convert_to_xdmf(meshio_mesh, output_path):
    # ... (keep original code) ...
    pass

def convert_to_stl(meshio_mesh, output_path):
    # ... (keep original code) ...
    pass

# -----------------------------------------------------------------------------
# Helper Functions - Data Processing (unchanged)
# -----------------------------------------------------------------------------
def get_variable_values(meshio_mesh, variable_name, faces):
    # ... (keep original code) ...
    pass

def get_available_variables(meshio_mesh):
    # ... (keep original code) ...
    pass

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

    # Session state for caching and cleanup
    if 'selected_group' not in st.session_state:
        st.session_state.selected_group = None          # dict of the selected group
    if 'combined_file_path' not in st.session_state:
        st.session_state.combined_file_path = None      # path to combined temp file (if split)
    if 'meshio_mesh' not in st.session_state:
        st.session_state.meshio_mesh = None
    if 'cache_dir' not in st.session_state:
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="moose_viewer_")
    if 'last_error' not in st.session_state:
        st.session_state.last_error = None

    # Clean up previous combined file when a new selection is made
    if st.session_state.combined_file_path and os.path.exists(st.session_state.combined_file_path):
        try:
            os.remove(st.session_state.combined_file_path)
        except:
            pass
        st.session_state.combined_file_path = None

    # -------------------------------------------------------------------------
    # Sidebar - File Selection
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.header("1. Select File Source")

        # Find grouped Exodus files in dataset folder
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

                # Create dropdown from groups
                display_names = [g['display_name'] for g in exodus_groups]
                selected_display = st.selectbox(
                    "Select Exodus File / Split Group",
                    display_names,
                    key="file_select",
                    index=0
                )
                # Find the corresponding group
                selected_group = next(g for g in exodus_groups if g['display_name'] == selected_display)

                # Show file info
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
                # Save uploaded file to cache
                tmp_filename = f"uploaded_{uploaded_file.name}"
                tmp_path = os.path.join(st.session_state.cache_dir, tmp_filename)
                try:
                    with open(tmp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    # Treat as a single-file group
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

    # -------------------------------------------------------------------------
    # Main Content - File Processing
    # -------------------------------------------------------------------------
    if selected_group is not None:
        # Determine the actual file path to load (combine parts if needed)
        if selected_group['part_files']:
            # This is a split group – combine parts into a temporary file
            combined_name = f"combined_{selected_group['base_name']}_{os.urandom(4).hex()}.e"
            combined_path = os.path.join(st.session_state.cache_dir, combined_name)
            if combine_parts(selected_group['part_files'], combined_path):
                load_path = combined_path
                st.session_state.combined_file_path = combined_path
            else:
                st.error("Failed to combine split files. Cannot load mesh.")
                load_path = None
        else:
            # Single file
            load_path = selected_group['single_file']
            st.session_state.combined_file_path = None

        # Check if we need to reload the mesh (group changed or first load)
        if load_path and (st.session_state.selected_group != selected_group or st.session_state.meshio_mesh is None):
            st.session_state.selected_group = selected_group
            st.session_state.meshio_mesh = None
            st.session_state.last_error = None

            meshio_mesh = load_exodus_data(load_path)
            if meshio_mesh is not None:
                st.session_state.meshio_mesh = meshio_mesh
                st.rerun()  # refresh to display visualization
            else:
                st.session_state.last_error = "Failed to load mesh"
        else:
            meshio_mesh = st.session_state.meshio_mesh

        # Display mesh if loaded successfully
        if meshio_mesh is not None:
            # Extract surface and get variables (same as original)
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

            # Download section (unchanged) ...
            st.divider()
            st.subheader("📥 Download for ParaView")
            # ... (rest of the download buttons exactly as in original)
            # (omitted here for brevity; keep the original download code)

        else:
            # Mesh loading failed
            st.error("❌ Failed to load mesh data. Please check the file format and try again.")
            if st.session_state.last_error:
                st.code(st.session_state.last_error)
    else:
        st.info("👈 Please select or upload an Exodus file from the sidebar to begin.")
        # Help/instructions expander (unchanged) ...

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <small>🦌 MOOSE Exodus Viewer v2.0 | Built with Streamlit + Plotly + Meshio | Split‑file support</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
