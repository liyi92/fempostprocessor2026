import streamlit as st
import meshio
import numpy as np
import tempfile
import os
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import base64
from io import BytesIO

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MOOSE Exodus Viewer", layout="wide")

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
        st.info("Tip: Ensure you have 'netCDF4' installed: `pip install netCDF4`")
        return None

def extract_mesh_surfaces(meshio_mesh):
    """
    Extract surface triangles from mesh for Plotly visualization.
    Works with tetrahedra and hexahedra.
    """
    points = meshio_mesh.points
    
    # Collect all faces from cells
    faces = []
    face_data = []  # To store scalar values for faces
    
    for cell_block in meshio_mesh.cells:
        cell_type = cell_block.type
        cells = cell_block.data
        
        if cell_type == 'tetra':
            # Each tetrahedron has 4 triangular faces
            for cell in cells:
                # Faces: (0,1,2), (0,1,3), (0,2,3), (1,2,3)
                tetra_faces = [
                    [cell[0], cell[1], cell[2]],
                    [cell[0], cell[1], cell[3]],
                    [cell[0], cell[2], cell[3]],
                    [cell[1], cell[2], cell[3]]
                ]
                faces.extend(tetra_faces)
                
        elif cell_type == 'hexahedron':
            # Each hexahedron has 6 quadrilateral faces
            # Convert quads to triangles for Plotly
            for cell in cells:
                # Faces of hexahedron
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
        
        elif cell_type == 'triangle':
            for cell in cells:
                faces.append(list(cell))
        
        elif cell_type == 'quad':
            for cell in cells:
                # Split quad into 2 triangles
                faces.append([cell[0], cell[1], cell[2]])
                faces.append([cell[0], cell[2], cell[3]])
    
    if len(faces) == 0:
        return None, None, None
    
    faces = np.array(faces)
    
    # Calculate face centers for scalar interpolation
    face_centers = np.mean(points[faces], axis=1)
    
    return points, faces, face_centers

def create_plotly_mesh(points, faces, values=None, color_map='Viridis', 
                       opacity=0.9, show_edges=False, title="Mesh"):
    """
    Create a Plotly 3D mesh visualization.
    """
    if points is None or faces is None:
        return go.Figure()
    
    # Extract triangle vertices
    i = faces[:, 0]
    j = faces[:, 1]
    k = faces[:, 2]
    
    # Create mesh3d figure
    fig = go.Figure(data=[go.Mesh3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        i=i,
        j=j,
        k=k,
        intensity=values,
        colorscale=color_map,
        opacity=opacity,
        showscale=values is not None,
        colorbar=dict(title=title) if values is not None else None,
        flatshading=True,
        lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.5, specular=0.2),
        lightposition=dict(x=0, y=0, z=0)
    )])
    
    if show_edges and len(faces) < 10000:  # Only show edges for smaller meshes
        edge_x = []
        edge_y = []
        edge_z = []
        
        for face in faces:
            for idx1, idx2 in [(0, 1), (1, 2), (2, 0)]:
                p1 = points[face[idx1]]
                p2 = points[face[idx2]]
                edge_x.extend([p1[0], p2[0], None])
                edge_y.extend([p1[1], p2[1], None])
                edge_z.extend([p1[2], p2[2], None])
        
        fig.add_trace(go.Scatter3d(
            x=edge_x, y=edge_y, z=edge_z,
            mode='lines',
            line=dict(color='black', width=1),
            name='Edges',
            opacity=0.5
        ))
    
    fig.update_layout(
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5)
            )
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        title=dict(text=title, x=0.5, xanchor='center')
    )
    
    return fig

def convert_to_vtu(meshio_mesh, output_path):
    """
    Convert meshio mesh to VTU format (ParaView compatible).
    """
    try:
        meshio.write(output_path, meshio_mesh)
        return True
    except Exception as e:
        st.error(f"Error converting to VTU: {e}")
        return False

def convert_to_vtp(meshio_mesh, output_path):
    """
    Convert meshio mesh to VTP format (PolyData, ParaView compatible).
    """
    try:
        # Create surface mesh for VTP
        points, faces, _ = extract_mesh_surfaces(meshio_mesh)
        if points is None:
            return False
        
        # Create new mesh with triangle cells
        triangle_cells = meshio.CellBlock('triangle', faces)
        surface_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
        
        # Copy point data if available
        if meshio_mesh.point_data:
            surface_mesh.point_data = meshio_mesh.point_data
        
        meshio.write(output_path, surface_mesh)
        return True
    except Exception as e:
        st.error(f"Error converting to VTP: {e}")
        return False

def convert_to_vtk(meshio_mesh, output_path):
    """
    Convert meshio mesh to legacy VTK format.
    """
    try:
        meshio.write(output_path, meshio_mesh)
        return True
    except Exception as e:
        st.error(f"Error converting to VTK: {e}")
        return False

def convert_to_xdmf(meshio_mesh, output_path):
    """
    Convert meshio mesh to XDMF format (ParaView compatible).
    """
    try:
        meshio.write(output_path, meshio_mesh)
        return True
    except Exception as e:
        st.error(f"Error converting to XDMF: {e}")
        return False

def get_file_size_mb(file_path):
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)

def get_file_display_name(file_path, base_dir):
    """Creates a user-friendly display name for the file."""
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
**Upload** a MOOSE simulation output file (`.exodus`, `.e`, or `.exo`) to visualize results interactively.
Files from the `dataset` folder are automatically detected. **Download** in ParaView-compatible formats.
""")

# Get the directory where app.py is located
app_dir = os.path.dirname(os.path.abspath(__file__))
dataset_dir = os.path.join(app_dir, "dataset")

# Initialize session state
if 'selected_file_path' not in st.session_state:
    st.session_state.selected_file_path = None
if 'meshio_mesh' not in st.session_state:
    st.session_state.meshio_mesh = None
if 'cache_dir' not in st.session_state:
    st.session_state.cache_dir = tempfile.mkdtemp()

# Sidebar for File Selection
with st.sidebar:
    st.header("1. Select File Source")
    
    # Find Exodus files in dataset folder
    exodus_files = find_exodus_files(dataset_dir)
    
    source_option = st.radio(
        "Choose file source:",
        ["Dataset Folder", "Upload File"],
        key="source_radio"
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
                list(file_options.keys()),
                key="file_select"
            )
            selected_file_path = file_options[selected_display]
            
            # Show file info
            file_size = get_file_size_mb(selected_file_path)
            st.info(f"📁 **Path:** `{selected_file_path}`\n\n📊 **Size:** {file_size:.2f} MB")
        else:
            st.warning(f"No Exodus files found in `dataset/` folder.\n\nPlease create the folder and add `.e` files.")
            st.code(f"Expected path: {dataset_dir}")
    else:
        st.subheader("Upload File")
        uploaded_file = st.file_uploader(
            "Choose an Exodus file",
            type=['e', 'exodus', 'exo', 'out'],
            key="file_uploader"
        )
        if uploaded_file:
            # Create temporary file
            tmp_path = os.path.join(st.session_state.cache_dir, uploaded_file.name)
            with open(tmp_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            selected_file_path = tmp_path
            st.info(f"📊 **Uploaded:** {uploaded_file.name}")

    st.divider()
    st.header("2. Visualization Settings")
    
    color_map = st.selectbox(
        "Color Map",
        ["Viridis", "Plasma", "Inferno", "Magma", "Cividis", 
         "Jet", "Rainbow", "Portland", "Blackbody", "Earth"],
        key="colormap_select"
    )
    opacity = st.slider("Opacity", 0.1, 1.0, 0.9, key="opacity_slider")
    show_edges = st.checkbox("Show Mesh Edges", value=False, key="edges_checkbox")
    show_scalar_bar = st.checkbox("Show Color Bar", value=True, key="scalarbar_checkbox")

# Main Content Area
if selected_file_path:
    # Check if we need to reload the mesh
    if (st.session_state.selected_file_path != selected_file_path or 
        st.session_state.meshio_mesh is None):
        
        st.session_state.selected_file_path = selected_file_path
        st.session_state.meshio_mesh = None
        
        # Load Data
        with st.spinner("Reading Exodus file..."):
            meshio_mesh = load_exodus_data(selected_file_path)
        
        if meshio_mesh:
            st.session_state.meshio_mesh = meshio_mesh
            st.rerun()
    else:
        meshio_mesh = st.session_state.meshio_mesh
    
    if meshio_mesh:
        # Extract surface for visualization
        with st.spinner("Processing mesh for visualization..."):
            points, faces, face_centers = extract_mesh_surfaces(meshio_mesh)
        
        # Identify available variables
        point_vars = list(meshio_mesh.point_data.keys()) if meshio_mesh.point_data else []
        cell_vars = list(meshio_mesh.cell_data.keys()) if meshio_mesh.cell_data else []
        all_vars = point_vars + cell_vars
        
        # Visualization Settings in Main Area
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            if not all_vars:
                st.warning("⚠️ No data variables found in the mesh. Visualizing geometry only.")
                variable_name = None
                values = None
            else:
                variable_name = st.selectbox(
                    "📊 Select Variable to Plot",
                    all_vars,
                    key="var_select"
                )
                
                # Get values for visualization
                values = None
                if variable_name:
                    if variable_name in point_vars:
                        # Interpolate point data to face centers
                        point_values = meshio_mesh.point_data[variable_name]
                        if point_values.ndim > 1:
                            # For vector data, use magnitude
                            point_values = np.linalg.norm(point_values, axis=1)
                        # Average point values for each face
                        values = np.mean(point_values[faces], axis=1)
                    elif variable_name in cell_vars:
                        # Use cell data directly
                        cell_values = meshio_mesh.cell_data[variable_name]
                        if isinstance(cell_values, list):
                            cell_values = np.concatenate(cell_values)
                        # Repeat for each face of each cell
                        n_cells = len(meshio_mesh.cells[0].data) if meshio_mesh.cells else 0
                        n_faces_per_cell = len(faces) // max(n_cells, 1)
                        values = np.repeat(cell_values, n_faces_per_cell)

        with col2:
            st.metric("🔵 Points", f"{meshio_mesh.points.shape[0]:,}")
        
        with col3:
            st.metric("🔷 Cells", f"{sum(len(c.data) for c in meshio_mesh.cells):,}")
        
        # Create Plotly Visualization
        if points is not None and faces is not None:
            fig = create_plotly_mesh(
                points, faces, values,
                color_map=color_map,
                opacity=opacity,
                show_edges=show_edges,
                title=variable_name if variable_name else "Mesh Geometry"
            )
            
            st.divider()
            st.subheader("🎨 3D Visualization")
            st.plotly_chart(fig, use_container_width=True, key="plotly_viz")
        else:
            st.error("❌ Could not extract mesh surfaces for visualization.")
        
        # Data Info & Download Section
        st.divider()
        st.subheader("📥 Download for ParaView")
        
        with st.expander("📋 Mesh & Data Information", expanded=False):
            st.write(f"**File:** `{selected_file_path}`")
            st.write(f"**Points:** {meshio_mesh.points.shape[0]:,}")
            st.write(f"**Cells:** {sum(len(c.data) for c in meshio_mesh.cells):,}")
            st.write(f"**Cell Types:** {[c.type for c in meshio_mesh.cells]}")
            
            if point_vars:
                st.write("**📍 Point Variables:**")
                for var in point_vars:
                    data = meshio_mesh.point_data[var]
                    st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
            
            if cell_vars:
                st.write("**🔷 Cell Variables:**")
                for var in cell_vars:
                    data = meshio_mesh.cell_data[var]
                    if isinstance(data, list):
                        data = np.concatenate(data)
                    st.write(f"  - `{var}`: shape={data.shape}, dtype={data.dtype}")
        
        # Download Buttons
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        
        with col_d1:
            # VTU Download
            vtu_path = os.path.join(st.session_state.cache_dir, "output.vtu")
            if convert_to_vtu(meshio_mesh, vtu_path):
                with open(vtu_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download .VTU",
                        data=f.read(),
                        file_name="mesh_output.vtu",
                        mime="application/xml",
                        key="download_vtu"
                    )
        
        with col_d2:
            # VTP Download
            vtp_path = os.path.join(st.session_state.cache_dir, "output.vtp")
            if convert_to_vtp(meshio_mesh, vtp_path):
                with open(vtp_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download .VTP",
                        data=f.read(),
                        file_name="mesh_surface.vtp",
                        mime="application/xml",
                        key="download_vtp"
                    )
        
        with col_d3:
            # VTK Download
            vtk_path = os.path.join(st.session_state.cache_dir, "output.vtk")
            if convert_to_vtk(meshio_mesh, vtk_path):
                with open(vtk_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download .VTK",
                        data=f.read(),
                        file_name="mesh_output.vtk",
                        mime="text/plain",
                        key="download_vtk"
                    )
        
        with col_d4:
            # XDMF Download
            xdmf_path = os.path.join(st.session_state.cache_dir, "output.xdmf")
            if convert_to_xdmf(meshio_mesh, xdmf_path):
                with open(xdmf_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download .XDMF",
                        data=f.read(),
                        file_name="mesh_output.xdmf",
                        mime="application/xml",
                        key="download_xdmf"
                    )
        
        st.info("""
        **💡 ParaView Instructions:**
        1. Download any format above (.vtu recommended)
        2. Open ParaView → File → Open → Select downloaded file
        3. Click "Apply" in Properties panel
        4. Use "Color By" dropdown to select variables
        """)
                
    else:
        st.error("❌ Failed to load mesh data.")
        
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
        ### 📁 Folder Structure
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
    <small>🦌 MOOSE Exodus Viewer | Built with Streamlit + Plotly + Meshio | ParaView Compatible Downloads</small>
</div>
""", unsafe_allow_html=True)

# Cleanup on session end (optional)
# Note: Streamlit doesn't have a clean session end hook, 
# but temp files will be cleaned by OS eventually
