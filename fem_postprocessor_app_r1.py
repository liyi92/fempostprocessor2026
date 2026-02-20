
import streamlit as st
import pyvista as pv
import meshio
import numpy as np
import tempfile
import os

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MOOSE Exodus Viewer", layout="wide")

# Configure PyVista to run off-screen (required for web servers)
pv.OFF_SCREEN = True

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def load_exodus_data(file_path):
    """
    Reads an Exodus file using meshio.
    Returns points, cells, and data dictionaries.
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
    # Extract points
    points = meshio_mesh.points
    
    # Extract cells (meshio stores them as a list of CellBlocks)
    # PyVista needs connectivity and offsets
    cells = []
    for block in meshio_mesh.cells:
        cell_type = block.type
        # Map meshio cell types to VTK cell types if necessary
        # meshio and pyvista usually align on standard names (tetra, hexahedron, etc.)
        data = block.data
        # PyVista expects connectivity array for unstructured grid
        # We need to prepend the number of points per cell to each row
        n_points = data.shape[1]
        # Create offset array (start index of each cell)
        # PyVista's UnstructuredGrid constructor is flexible, 
        # but easiest is to pass cells as a dict {cell_type: data}
        cells.append((cell_type, data))
        
    grid = pv.UnstructuredGrid(cells, points)
    
    # Add Point Data
    if meshio_mesh.point_data:
        for name, data in meshio_mesh.point_data.items():
            # Ensure data is contiguous and float for VTK
            grid.point_data[name] = data
            
    # Add Cell Data
    if meshio_mesh.cell_data:
        for name, data in meshio_mesh.cell_data.items():
            # meshio cell_data is a list of arrays per cell block
            # We need to concatenate them if there are multiple blocks of same type
            # Or simply add them. PyVista handles mapping if lengths match cells.
            # Simple approach: flatten if needed
            if isinstance(data, list):
                data = np.concatenate(data)
            grid.cell_data[name] = data
            
    return grid

# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------
st.title("🦌 MOOSE Exodus Output Viewer")
st.markdown("""
Upload a MOOSE simulation output file (`.exodus`, `.e`, or `.exo`) to visualize results interactively.
""")

# Sidebar for File Upload
with st.sidebar:
    st.header("1. Upload File")
    uploaded_file = st.file_uploader("Choose an Exodus file", type=['e', 'exodus', 'exo', 'out'])
    
    st.divider()
    st.header("2. Visualization Settings")
    
    # Placeholder for controls that depend on file loading
    variable_name = None
    color_map = st.selectbox("Color Map", ["viridis", "plasma", "coolwarm", "jet", "gray"])
    opacity = st.slider("Opacity", 0.1, 1.0, 1.0)
    show_edges = st.checkbox("Show Mesh Edges", value=False)
    clip_enabled = st.checkbox("Enable Clipping Plane", value=False)

# Main Content Area
if uploaded_file is not None:
    # Create a temporary file on disk because meshio/pyvista need a path, not bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix='.e') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Load Data
        with st.spinner("Reading Exodus file..."):
            meshio_mesh = load_exodus_data(tmp_path)
        
        if meshio_mesh:
            # Convert to PyVista
            grid = create_pyvista_grid(meshio_mesh)
            
            # Identify available variables
            point_vars = list(grid.point_data.keys())
            cell_vars = list(grid.cell_data.keys())
            all_vars = point_vars + cell_vars
            
            if not all_vars:
                st.warning("No data variables found in the mesh. Visualizing geometry only.")
                variable_name = None
            else:
                variable_name = st.selectbox("Select Variable to Plot", all_vars)
                # Determine if it's point or cell data for active scalars
                if variable_name in point_vars:
                    grid.set_active_scalars(variable_name, preference="point")
                else:
                    grid.set_active_scalars(variable_name, preference="cell")

            # Create Plotter
            plotter = pv.Plotter()
            plotter.add_mesh(grid, 
                             scalars=variable_name, 
                             cmap=color_map, 
                             opacity=opacity, 
                             show_edges=show_edges,
                             show_scalar_bar=True)
            
            # Add Clipping Plane if requested
            if clip_enabled and variable_name:
                plotter.add_clip_widget()

            # Set camera position (isometric view)
            plotter.camera_position = 'iso'
            
            # Display in Streamlit
            st.subheader(f"3D Visualization: {variable_name if variable_name else 'Geometry'}")
            st.pyvista_chart(plotter, height=600, key="viz")
            
            # Data Info
            with st.expander("Mesh Information"):
                st.write(f"**Points:** {grid.n_points}")
                st.write(f"**Cells:** {grid.n_cells}")
                st.write(f"**Point Variables:** {point_vars}")
                st.write(f"**Cell Variables:** {cell_vars}")
                
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
else:
    st.info("Please upload an Exodus file from the sidebar to begin.")
    
    # Demo Placeholder
    with st.expander("Don't have a file? See expected format"):
        st.code("""
        # MOOSE input file snippet to ensure Exodus output
        [Outputs]
          exodus = true
          file_base = my_simulation
        []
        """)
