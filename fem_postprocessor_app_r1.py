import streamlit as st
import pyvista as pv
import meshio
import numpy as np
import tempfile
import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MOOSE Exodus Viewer", layout="wide")

# Configure PyVista to run off-screen (required for web servers)
pv.OFF_SCREEN = True

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def find_exodus_files(search_dir):
    """
    Recursively find all Exodus files in the given directory.
    Returns a list of file paths.
    """
    exodus_extensions = ['.e', '.exo', '.exodus', '.out']
    exodus_files = []
    
    if not os.path.exists(search_dir):
        return exodus_files
    
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in exodus_extensions:
                exodus_files.append(os.path.join(root, file))
    
    # Sort files alphabetically
    exodus_files.sort()
    return exodus_files

def load_exodus_data(file_path):
    """
    Reads an Exodus file using meshio.
    Returns meshio mesh object.
    """
    try:
        mesh = meshio.read(file_path)
        return mesh
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.info("Tip: Ensure you have 'netCDF4' installed. For best compatibility, use Conda with 'seacas'.")
        return None

def create_pyvista_grid(meshio_mesh):
    """
    Converts a meshio mesh object to a PyVista UnstructuredGrid.
    """
    points = meshio_mesh.points
    cells = []
    
    for block in meshio_mesh.cells:
        cell_type = block.type
        data = block.data
        cells.append((cell_type, data))
        
    grid = pv.UnstructuredGrid(cells, points)
    
    # Add Point Data
    if meshio_mesh.point_data:
        for name, data in meshio_mesh.point_data.items():
            grid.point_data[name] = data
            
    # Add Cell Data
    if meshio_mesh.cell_data:
        for name, data in meshio.cell_data.items():
            if isinstance(data, list):
                data = np.concatenate(data)
            grid.cell_data[name] = data
            
    return grid

def get_file_display_name(file_path, base_dir):
    """
    Creates a user-friendly display name for the file.
    """
    try:
        rel_path = os.path.relpath(file_path, base_dir)
        return rel_path
    except:
        return os.path.basename(file_path)

# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------
st.title("🦌 MOOSE Exodus Output Viewer")
st.markdown("""
Upload a MOOSE simulation output file (`.exodus`, `.e`, or `.exo`) to visualize results interactively.
Files from the `dataset` folder are automatically detected.
""")

# Get the directory where app.py is located
app_dir = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(app_dir, "dataset")

# Sidebar for File Selection
with st.sidebar:
    st.header("1. Select File Source")
    
    # Find Exodus files in dataset folder
    exodus_files = find_exodus_files(dataset_dir)
    
    source_option = st.radio(
        "Choose file source:",
        ["Dataset Folder", "Upload File"]
    )
    
    selected_file_path = None
    
    if source_option == "Dataset Folder":
        st.subheader("Dataset Files")
        if exodus_files:
            st.success(f"Found {len(exodus_files)} Exodus file(s) in `dataset/`")
            
            # Create display names for dropdown
            file_options = {}
            for f in exodus_files:
                display_name = get_file_display_name(f, app_dir)
                file_options[display_name] = f
            
            selected_display = st.selectbox(
                "Select Exodus File",
                list(file_options.keys())
            )
            selected_file_path = file_options[selected_display]
            
            # Show file info
            file_size = os.path.getsize(selected_file_path) / (1024 * 1024)
            st.info(f"📁 **Path:** `{selected_file_path}`\n\n📊 **Size:** {file_size:.2f} MB")
        else:
            st.warning(f"No Exodus files found in `dataset/` folder.\n\nPlease create the folder and add `.e` files.")
            st.code(f"Expected path: {dataset_dir}")
    else:
        st.subheader("Upload File")
        uploaded_file = st.file_uploader(
            "Choose an Exodus file",
            type=['e', 'exodus', 'exo', 'out']
        )
        if uploaded_file:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.e') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                selected_file_path = tmp_file.name
            st.info(f"📊 **Uploaded:** {uploaded_file.name}")

    st.divider()
    st.header("2. Visualization Settings")
    
    color_map = st.selectbox(
        "Color Map",
        ["viridis", "plasma", "coolwarm", "jet", "gray", "inferno", "magma", "cividis"]
    )
    opacity = st.slider("Opacity", 0.1, 1.0, 1.0)
    show_edges = st.checkbox("Show Mesh Edges", value=False)
    clip_enabled = st.checkbox("Enable Clipping Plane", value=False)
    show_scalar_bar = st.checkbox("Show Color Bar", value=True)

# Main Content Area
if selected_file_path:
    try:
        # Load Data
        with st.spinner("Reading Exodus file..."):
            meshio_mesh = load_exodus_data(selected_file_path)
        
        if meshio_mesh:
            # Convert to PyVista
            grid = create_pyvista_grid(meshio_mesh)
            
            # Identify available variables
            point_vars = list(grid.point_data.keys())
            cell_vars = list(grid.cell_data.keys())
            all_vars = point_vars + cell_vars
            
            # Visualization Settings in Main Area
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if not all_vars:
                    st.warning("No data variables found in the mesh. Visualizing geometry only.")
                    variable_name = None
                else:
                    variable_name = st.selectbox(
                        "📊 Select Variable to Plot",
                        all_vars,
                        key="var_select"
                    )
                    # Determine if it's point or cell data for active scalars
                    if variable_name in point_vars:
                        grid.set_active_scalars(variable_name, preference="point")
                    else:
                        grid.set_active_scalars(variable_name, preference="cell")

            with col2:
                st.metric("Points", grid.n_points)
                st.metric("Cells", grid.n_cells)
                st.metric("Variables", len(all_vars))
            
            # Create Plotter
            plotter = pv.Plotter()
            plotter.add_mesh(
                grid,
                scalars=variable_name,
                cmap=color_map,
                opacity=opacity,
                show_edges=show_edges,
                show_scalar_bar=show_scalar_bar
            )
            
            # Add Clipping Plane if requested
            if clip_enabled and variable_name:
                plotter.add_clip_widget()

            # Set camera position (isometric view)
            plotter.camera_position = 'iso'
            
            # Display in Streamlit
            st.divider()
            st.subheader(f"3D Visualization: {variable_name if variable_name else 'Geometry'}")
            st.pyvista_chart(plotter, height=600, key="viz")
            
            # Data Info Expander
            with st.expander("📋 Mesh & Data Information"):
                st.write(f"**File:** `{selected_file_path}`")
                st.write(f"**Points:** {grid.n_points:,}")
                st.write(f"**Cells:** {grid.n_cells:,}")
                
                if point_vars:
                    st.write("**Point Variables:**")
                    for var in point_vars:
                        data = grid.point_data[var]
                        st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
                
                if cell_vars:
                    st.write("**Cell Variables:**")
                    for var in cell_vars:
                        data = grid.cell_data[var]
                        st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
                
                # Download option for processed data
                st.download_button(
                    label="📥 Download Mesh Info as JSON",
                    data=str({
                        "points": grid.n_points,
                        "cells": grid.n_cells,
                        "point_vars": point_vars,
                        "cell_vars": cell_vars
                    }),
                    file_name="mesh_info.txt",
                    mime="text/plain"
                )
                
    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.exception(e)
        
    finally:
        # Clean up temp file if it was an upload (not from dataset)
        if source_option == "Upload File" and os.path.exists(selected_file_path):
            try:
                os.remove(selected_file_path)
            except:
                pass
else:
    st.info("👈 Please select or upload an Exodus file from the sidebar to begin.")
    
    # Demo Placeholder
    with st.expander("📖 Don't have a file? See expected format"):
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
        """)
        
        st.markdown("""
        ### Folder Structure
        ```
        your_project/
        ├── app.py
        └── dataset/
            ├── two_phase_output.e
            ├── simulation_1.e
            └── simulation_2.e
        ```
        """)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>MOOSE Exodus Viewer | Built with Streamlit + PyVista + Meshio</small>
</div>
""", unsafe_allow_html=True)
