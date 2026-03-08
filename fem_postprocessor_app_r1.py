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
from io import BytesIO, StringIO
import warnings
import re
import math
from datetime import datetime
import pandas as pd
from collections import defaultdict
import logging
from typing import Optional, Dict, List, Tuple, Union, Any
warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('moose_viewer.log', mode='a')
    ]
)
logger = logging.getLogger('MOOSEViewer')

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MOOSE Exodus Viewer Pro",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://mooseframework.inl.gov',
        'Report a bug': 'https://github.com/idaholab/moose/issues',
        'About': "MOOSE Exodus Viewer Pro v4.0\nBuilt with Streamlit + Plotly + Meshio + NetCDF4"
    }
)

# -----------------------------------------------------------------------------
# Custom CSS for Better UI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1f77b4;
    text-align: center;
    padding: 1rem 0;
    border-bottom: 3px solid #1f77b4;
    margin-bottom: 1.5rem;
}
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
    padding: 1rem;
    color: white;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.metric-value {
    font-size: 2rem;
    font-weight: bold;
}
.metric-label {
    font-size: 0.9rem;
    opacity: 0.9;
}
.download-btn {
    width: 100%;
    margin: 0.25rem 0;
}
.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 5px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.warning-box {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 5px;
    padding: 1rem;
    margin: 0.5rem 0;
}
.error-box {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 5px;
    padding: 1rem;
    margin: 0.5rem 0;
}
div[data-testid="stExpander"] {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
}
pre {
    max-height: 400px;
    overflow-y: auto;
}
.viz-toggle {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Export Formats - VERIFIED meshio supported formats only
# -----------------------------------------------------------------------------
SUPPORTED_EXPORT_FORMATS = {
    'vtu': {
        'name': 'VTU (Unstructured Grid)',
        'ext': '.vtu',
        'mime': 'application/xml',
        'desc': 'Full 3D mesh with all variables (RECOMMENDED for ParaView)',
        'surface_only': False,
        'supports_timeseries': True
    },
    'vtk': {
        'name': 'VTK (Legacy)',
        'ext': '.vtk',
        'mime': 'text/plain',
        'desc': 'Legacy VTK format (widely compatible)',
        'surface_only': False,
        'supports_timeseries': False
    },
    'stl': {
        'name': 'STL (Surface)',
        'ext': '.stl',
        'mime': 'application/sla',
        'desc': 'Surface mesh for CAD/3D printing (no scalar data)',
        'surface_only': True,
        'supports_timeseries': False
    },
    'ply': {
        'name': 'PLY (Polygon)',
        'ext': '.ply',
        'mime': 'application/octet-stream',
        'desc': 'Surface with vertex colors/data (good for visualization)',
        'surface_only': True,
        'supports_timeseries': False
    },
    'xdmf': {
        'name': 'XDMF (Large Data)',
        'ext': '.xdmf',
        'mime': 'application/xml',
        'desc': 'XDMF for large datasets with time series (requires h5py)',
        'surface_only': False,
        'requires': ['h5py'],
        'supports_timeseries': True
    },
    'exodus': {
        'name': 'Exodus (MOOSE Native)',
        'ext': '.e',
        'mime': 'application/octet-stream',
        'desc': 'Native MOOSE format (for re-import)',
        'surface_only': False,
        'supports_timeseries': True
    },
}

# -----------------------------------------------------------------------------
# Helper Functions - File Discovery
# -----------------------------------------------------------------------------
def find_exodus_files(search_dir: str, recursive: bool = True) -> List[str]:
    """
    Recursively find all Exodus files in the given directory.
    
    Args:
        search_dir: Directory path to search
        recursive: Whether to search subdirectories
        
    Returns:
        list: Sorted list of file paths
    """
    exodus_extensions = ['.e', '.exo', '.exodus', '.out', '.ex2', '.e-s001', '.e-s002']
    exodus_files = []
    
    if not os.path.exists(search_dir):
        logger.warning(f"Directory not found: {search_dir}")
        return exodus_files
    
    try:
        if recursive:
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden and cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in exodus_extensions or re.match(r'\.e-s\d+$', file_ext):
                        full_path = os.path.join(root, file)
                        exodus_files.append(full_path)
        else:
            for file in os.listdir(search_dir):
                if file.startswith('.'):
                    continue
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in exodus_extensions or re.match(r'\.e-s\d+$', file_ext):
                    full_path = os.path.join(search_dir, file)
                    exodus_files.append(full_path)
    except PermissionError as e:
        logger.warning(f"Permission denied: {search_dir}")
        st.warning(f"Permission denied accessing: {search_dir}")
    except Exception as e:
        logger.error(f"Error scanning directory {search_dir}: {e}")
        st.warning(f"Error scanning directory: {e}")
    
    exodus_files.sort(key=lambda x: (os.path.dirname(x), os.path.basename(x).lower()))
    logger.info(f"Found {len(exodus_files)} Exodus files in {search_dir}")
    return exodus_files

def get_file_display_name(file_path: str, base_dir: str) -> str:
    """Creates a user-friendly display name showing relative path."""
    try:
        rel_path = os.path.relpath(file_path, base_dir)
        if os.path.dirname(rel_path):
            return f"📁 {rel_path}"
        return f"📄 {os.path.basename(file_path)}"
    except ValueError:
        return f"📄 {os.path.basename(file_path)}"
    except Exception:
        return os.path.basename(file_path)

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB with error handling."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0

def format_file_size(size_mb: float) -> str:
    """Format file size with appropriate units."""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    elif size_mb < 100:
        return f"{size_mb:.2f} MB"
    else:
        return f"{size_mb:.1f} MB"

# -----------------------------------------------------------------------------
# Helper Functions - NetCDF4 Time-Step Reading (Core Enhancement)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Reading Exodus file metadata...")
def read_exodus_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read Exodus file metadata using netCDF4 to get time info and variable names.
    Returns dict with time_values, n_times, variable info.
    """
    try:
        from netCDF4 import Dataset
    except ImportError:
        logger.error("netCDF4 not installed")
        return None
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    
    try:
        with Dataset(file_path, 'r') as nc:
            metadata = {
                'time_values': None,
                'n_times': 1,
                'point_vars': [],
                'cell_vars': [],
                'displacement_vars': [],
                'vector_vars': {},
                'scalar_vars': {}
            }
            
            # Get time values
            if 'time_whole' in nc.variables:
                metadata['time_values'] = nc.variables['time_whole'][:]
                metadata['n_times'] = len(metadata['time_values'])
            elif 'time' in nc.variables:
                metadata['time_values'] = nc.variables['time'][:]
                metadata['n_times'] = len(metadata['time_values'])
            elif 'time' in nc.dimensions:
                metadata['n_times'] = nc.dimensions['time'].size
            elif 'num_time_steps' in nc.dimensions:
                metadata['n_times'] = nc.dimensions['num_time_steps'].size
            
            # Read nodal variable names
            if 'num_nod_var' in nc.dimensions:
                num_nod_vars = nc.dimensions['num_nod_var'].size
                for k in range(num_nod_vars):
                    var_name_key = f'name_nod_var{k+1}'
                    if var_name_key in nc.variables:
                        var_name = nc.variables[var_name_key][:]
                        if isinstance(var_name, np.ndarray):
                            var_name = var_name.tobytes().decode('utf-8', errors='ignore').strip('\x00')
                        else:
                            var_name = str(var_name).strip()
                        if var_name:
                            metadata['point_vars'].append(var_name)
                            # Detect displacement variables
                            if var_name in ['disp_x', 'disp_y', 'disp_z', 'displacement_x', 'displacement_y', 'displacement_z']:
                                metadata['displacement_vars'].append(var_name)
                            # Detect vector variables (common patterns)
                            if var_name in ['velocity', 'velocity_x', 'velocity_y', 'velocity_z', 
                                           'flux', 'flux_x', 'flux_y', 'flux_z',
                                           'gradient', 'grad_x', 'grad_y', 'grad_z']:
                                metadata['vector_vars'][var_name] = 'nodal'
                            else:
                                metadata['scalar_vars'][var_name] = 'nodal'
            
            # Read elemental variable names
            if 'num_elem_var' in nc.dimensions:
                num_elem_vars = nc.dimensions['num_elem_var'].size
                for k in range(num_elem_vars):
                    var_name_key = f'name_elem_var{k+1}'
                    if var_name_key in nc.variables:
                        var_name = nc.variables[var_name_key][:]
                        if isinstance(var_name, np.ndarray):
                            var_name = var_name.tobytes().decode('utf-8', errors='ignore').strip('\x00')
                        else:
                            var_name = str(var_name).strip()
                        if var_name:
                            metadata['cell_vars'].append(var_name)
                            if var_name in ['stress', 'strain', 'flux_elem']:
                                metadata['vector_vars'][var_name] = 'elemental'
                            else:
                                metadata['scalar_vars'][var_name] = 'elemental'
            
            logger.info(f"Metadata: {metadata['n_times']} timesteps, {len(metadata['point_vars'])} point vars, {len(metadata['cell_vars'])} cell vars")
            return metadata
    
    except Exception as e:
        logger.error(f"Error reading metadata: {e}")
        return None

@st.cache_data(ttl=3600, show_spinner="Loading Exodus data...")
def read_exodus_all_timesteps(file_path: str, time_step: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Read Exodus file data using netCDF4 directly for all or selected time steps.
    Supports lazy loading via time_step parameter.
    
    Returns:
        dict with keys:
            - 'mesh': meshio mesh with topology
            - 'time_values': array of time values
            - 'n_times': number of time steps
            - 'point_data_all': dict of {var_name: (n_times, n_points, [components])}
            - 'cell_data_all': dict of {var_name: (n_times, n_cells, [components])}
            - 'base_points': original coordinates (for deforming mesh support)
            - 'point_vars': list of point variable names
            - 'cell_vars': list of cell variable names
            - 'displacement_vars': list of displacement variable names
            - 'vector_vars': dict of vector variable metadata
    """
    try:
        from netCDF4 import Dataset
    except ImportError:
        st.error("netCDF4 library not installed. Please install with: pip install netCDF4")
        logger.error("netCDF4 not available")
        return None
    
    if not os.path.exists(file_path):
        st.error(f"File not found: {file_path}")
        return None
    
    try:
        with st.spinner(f"Reading {os.path.basename(file_path)}..."):
            # Read mesh topology with meshio (static) - explicit format for partitioned files
            mesh = meshio.read(file_path, file_format="exodus")
            
            if mesh.points is None or len(mesh.points) == 0:
                logger.warning("Mesh has no points")
                st.warning("Mesh has no points. File may be empty or corrupted.")
                return None
            
            with Dataset(file_path, 'r') as nc:
                # Get time values
                time_values = None
                n_times = 1
                if 'time_whole' in nc.variables:
                    time_values = nc.variables['time_whole'][:]
                    n_times = len(time_values)
                elif 'time' in nc.variables:
                    time_values = nc.variables['time'][:]
                    n_times = len(time_values)
                elif 'time' in nc.dimensions:
                    n_times = nc.dimensions['time'].size
                elif 'num_time_steps' in nc.dimensions:
                    n_times = nc.dimensions['num_time_steps'].size
                
                # Store base points for deforming mesh support
                base_points = np.asarray(mesh.points).copy()
                
                # Initialize data containers
                point_data_all = {}
                cell_data_all = {}
                displacement_vars = []
                vector_vars = {}
                
                # Determine which time steps to load (for lazy loading)
                if time_step is None:
                    time_indices = list(range(n_times))
                elif isinstance(time_step, int):
                    time_indices = [time_step]
                elif isinstance(time_step, (list, tuple)):
                    time_indices = list(time_step)
                else:
                    time_indices = list(range(n_times))
                
                # Read nodal (point) variables
                if 'num_nod_var' in nc.dimensions:
                    num_nod_vars = nc.dimensions['num_nod_var'].size
                    for k in range(num_nod_vars):
                        var_name_key = f'name_nod_var{k+1}'
                        if var_name_key in nc.variables:
                            var_name = nc.variables[var_name_key][:]
                            if isinstance(var_name, np.ndarray):
                                var_name = var_name.tobytes().decode('utf-8', errors='ignore').strip('\x00')
                            else:
                                var_name = str(var_name).strip()
                            
                            if var_name:
                                vals_var = f'vals_nod_var{k+1}'
                                if vals_var in nc.variables:
                                    # Load data - shape: (time, nodes) or (time, nodes, components)
                                    full_data = nc.variables[vals_var][:]
                                    
                                    # Slice to requested time steps if needed
                                    if time_indices != list(range(n_times)):
                                        data = full_data[time_indices]
                                    else:
                                        data = full_data
                                    
                                    point_data_all[var_name] = data
                                    
                                    # Track displacement variables
                                    if var_name in ['disp_x', 'disp_y', 'disp_z', 'displacement_x', 'displacement_y', 'displacement_z']:
                                        displacement_vars.append(var_name)
                                    
                                    # Track vector variables
                                    if data.ndim >= 3 and data.shape[-1] in [2, 3]:
                                        vector_vars[var_name] = {'location': 'point', 'components': data.shape[-1]}
                
                # Read elemental (cell) variables
                if 'num_elem_var' in nc.dimensions:
                    num_elem_vars = nc.dimensions['num_elem_var'].size
                    for k in range(num_elem_vars):
                        var_name_key = f'name_elem_var{k+1}'
                        if var_name_key in nc.variables:
                            var_name = nc.variables[var_name_key][:]
                            if isinstance(var_name, np.ndarray):
                                var_name = var_name.tobytes().decode('utf-8', errors='ignore').strip('\x00')
                            else:
                                var_name = str(var_name).strip()
                            
                            if var_name:
                                vals_var = f'vals_elem_var{k+1}'
                                if vals_var in nc.variables:
                                    full_data = nc.variables[vals_var][:]
                                    if time_indices != list(range(n_times)):
                                        data = full_data[time_indices]
                                    else:
                                        data = full_data
                                    cell_data_all[var_name] = data
                                    
                                    if data.ndim >= 3 and data.shape[-1] in [2, 3]:
                                        vector_vars[var_name] = {'location': 'cell', 'components': data.shape[-1]}
                
                # Merge meshio's point_data for any additional variables
                if mesh.point_data:
                    for var_name, data in mesh.point_data.items():
                        if var_name not in point_data_all:
                            # Expand single timestep to match n_times
                            if data.ndim == 1:
                                expanded = np.tile(data, (n_times, 1))
                            elif data.ndim == 2:
                                expanded = np.tile(data, (n_times, 1, 1))
                            else:
                                expanded = data
                            point_data_all[var_name] = expanded
                
                if mesh.cell_data:
                    for var_name, data_list in mesh.cell_data.items():
                        if var_name not in cell_data_all:
                            if isinstance(data_list, list) and len(data_list) > 0:
                                data = np.concatenate([np.asarray(d) for d in data_list if d is not None])
                            else:
                                data = np.asarray(data_list)
                            if data.ndim == 1:
                                expanded = np.tile(data, (n_times, 1))
                            elif data.ndim == 2:
                                expanded = np.tile(data, (n_times, 1, 1))
                            else:
                                expanded = data
                            cell_data_all[var_name] = expanded
                
                return {
                    'mesh': mesh,
                    'time_values': time_values,
                    'n_times': n_times,
                    'point_data_all': point_data_all,
                    'cell_data_all': cell_data_all,
                    'base_points': base_points,
                    'point_vars': sorted(point_data_all.keys()),
                    'cell_vars': sorted(cell_data_all.keys()),
                    'displacement_vars': displacement_vars,
                    'vector_vars': vector_vars
                }
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        st.error(f"Missing dependency: {e}")
        if 'netcdf' in str(e).lower():
            st.info("Install with: `pip install netCDF4`")
        elif 'h5py' in str(e).lower():
            st.info("Install with: `pip install h5py`")
        return None
    except Exception as e:
        logger.error(f"Error reading file: {type(e).__name__}: {e}")
        st.error(f"Error reading Exodus file: {type(e).__name__}: {str(e)[:200]}")
        with st.expander("Technical Details", expanded=False):
            st.code(f"File: {file_path}\nError: {type(e).__name__}: {str(e)}", language="text")
        return None

def load_exodus_data(file_path: str, time_step: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Wrapper for backward compatibility.
    FIXED: Parameter name is 'time_step', not 'time_step_slice'
    """
    return read_exodus_all_timesteps(file_path, time_step=time_step)

# -----------------------------------------------------------------------------
# Helper Functions - Mesh Analysis with Time Support
# -----------------------------------------------------------------------------
# REMOVED @st.cache_data decorator because mesh_data dict contains unhashable objects
def analyze_mesh(mesh_data: Dict[str, Any], time_step: int = 0) -> Dict[str, Any]:
    """
    Analyze mesh and return statistics dictionary for specified time step.
    Handles deforming meshes and vector fields.
    """
    if mesh_data is None:
        return {}
    
    mesh = mesh_data.get('mesh')
    if mesh is None:
        return {}
    
    stats = {
        'n_points': len(mesh.points) if mesh.points is not None else 0,
        'n_cells': 0,
        'cell_types': {},
        'dimensions': None,
        'bounds': None,
        'point_vars': mesh_data.get('point_vars', []),
        'cell_vars': mesh_data.get('cell_vars', []),
        'field_info': {},
        'n_times': mesh_data.get('n_times', 1),
        'time_values': mesh_data.get('time_values'),
        'displacement_vars': mesh_data.get('displacement_vars', []),
        'vector_vars': mesh_data.get('vector_vars', {}),
        'is_deforming': False
    }
    
    # Count cells by type
    if mesh.cells:
        for cell_block in mesh.cells:
            if cell_block and cell_block.data is not None:
                cell_type = cell_block.type or 'unknown'
                n_cells = len(cell_block.data)
                stats['n_cells'] += n_cells
                stats['cell_types'][cell_type] = stats['cell_types'].get(cell_type, 0) + n_cells
    
    # Get dimensions and bounds
    if mesh.points is not None and len(mesh.points) > 0:
        points = np.asarray(mesh.points)
        stats['dimensions'] = points.shape[1] if points.ndim > 1 else 1
        stats['bounds'] = {
            'x': (float(np.min(points[:, 0])), float(np.max(points[:, 0]))),
            'y': (float(np.min(points[:, 1])), float(np.max(points[:, 1]))) if points.shape[1] > 1 else None,
            'z': (float(np.min(points[:, 2])), float(np.max(points[:, 2]))) if points.shape[1] > 2 else None,
        }
    
    # Check if mesh is deforming
    disp_vars = stats['displacement_vars']
    if len(disp_vars) >= 2:  # Need at least x and y
        stats['is_deforming'] = True
        logger.info(f"Detected deforming mesh with displacement vars: {disp_vars}")
    
    # Compute variable ranges for the specified time step
    point_data_all = mesh_data.get('point_data_all', {})
    cell_data_all = mesh_data.get('cell_data_all', {})
    vector_vars = stats['vector_vars']
    
    for var_name in stats['point_vars']:
        if var_name in point_data_all:
            data = point_data_all[var_name]
            try:
                if data.ndim >= 2:
                    # Get data for specified time step
                    ts_idx = min(time_step, data.shape[0] - 1)
                    ts_data = data[ts_idx]
                    
                    # Check if vector field
                    is_vector = var_name in vector_vars or (ts_data.ndim > 1 and ts_data.shape[-1] in [2, 3])
                    
                    if is_vector and ts_data.ndim > 1:
                        # Compute magnitude for range
                        mag = np.linalg.norm(ts_data, axis=-1)
                        global_min = float(np.min(mag))
                        global_max = float(np.max(mag))
                        shape = ts_data.shape[1:]
                        dtype = 'vector'
                    else:
                        global_min = float(np.min(ts_data))
                        global_max = float(np.max(ts_data))
                        shape = ts_data.shape[1:] if ts_data.ndim > 1 else ()
                        dtype = str(ts_data.dtype)
                    
                    stats['field_info'][var_name] = {
                        'location': 'point',
                        'shape': shape,
                        'dtype': dtype,
                        'range': (global_min, global_max),
                        'n_times': data.shape[0] if data.ndim >= 2 else 1,
                        'is_vector': is_vector
                    }
            except Exception as e:
                logger.warning(f"Error analyzing {var_name}: {e}")
                stats['field_info'][var_name] = {}
    
    for var_name in stats['cell_vars']:
        if var_name in cell_data_all:
            data = cell_data_all[var_name]
            try:
                if data.ndim >= 2:
                    ts_idx = min(time_step, data.shape[0] - 1)
                    ts_data = data[ts_idx]
                    
                    is_vector = var_name in vector_vars or (ts_data.ndim > 1 and ts_data.shape[-1] in [2, 3])
                    
                    if is_vector and ts_data.ndim > 1:
                        mag = np.linalg.norm(ts_data, axis=-1)
                        global_min = float(np.min(mag))
                        global_max = float(np.max(mag))
                        shape = ts_data.shape[1:]
                        dtype = 'vector'
                    else:
                        global_min = float(np.min(ts_data))
                        global_max = float(np.max(ts_data))
                        shape = ts_data.shape[1:] if ts_data.ndim > 1 else ()
                        dtype = str(ts_data.dtype)
                    
                    stats['field_info'][var_name] = {
                        'location': 'cell',
                        'shape': shape,
                        'dtype': dtype,
                        'range': (global_min, global_max),
                        'n_times': data.shape[0] if data.ndim >= 2 else 1,
                        'is_vector': is_vector
                    }
            except Exception as e:
                logger.warning(f"Error analyzing {var_name}: {e}")
                stats['field_info'][var_name] = {}
    
    return stats

# -----------------------------------------------------------------------------
# Helper Functions - Mesh Merging
# -----------------------------------------------------------------------------
def merge_meshes(meshes_data_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge a list of mesh data dicts from parallel subdomains."""
    if not meshes_data_list:
        return None
    if len(meshes_data_list) == 1:
        return meshes_data_list[0]
    
    # Merge topology
    meshio_meshes = [md['mesh'] for md in meshes_data_list if md.get('mesh')]
    merged_mesh = merge_meshio_meshes(meshio_meshes)
    
    if merged_mesh is None:
        return None
    
    # Merge metadata
    n_times = max(md.get('n_times', 1) for md in meshes_data_list)
    time_values = None
    for md in meshes_data_list:
        if md.get('time_values') is not None:
            time_values = md['time_values']
            break
    
    # Merge point data (concatenate along node axis)
    point_data_all = {}
    point_vars = set()
    for md in meshes_data_list:
        for var, data in md.get('point_data_all', {}).items():
            point_vars.add(var)
            if var not in point_data_all:
                point_data_all[var] = []
            point_data_all[var].append(data)
    
    for var in point_vars:
        if var in point_data_all and len(point_data_all[var]) > 1:
            point_data_all[var] = np.concatenate(point_data_all[var], axis=1)
        elif var in point_data_all:
            point_data_all[var] = point_data_all[var][0]
    
    # Merge cell data
    cell_data_all = {}
    cell_vars = set()
    for md in meshes_data_list:
        for var, data in md.get('cell_data_all', {}).items():
            cell_vars.add(var)
            if var not in cell_data_all:
                cell_data_all[var] = []
            cell_data_all[var].append(data)
    
    for var in cell_vars:
        if var in cell_data_all and len(cell_data_all[var]) > 1:
            cell_data_all[var] = np.concatenate(cell_data_all[var], axis=1)
        elif var in cell_data_all:
            cell_data_all[var] = cell_data_all[var][0]
    
    # Merge displacement vars and vector vars
    displacement_vars = set()
    vector_vars = {}
    for md in meshes_data_list:
        displacement_vars.update(md.get('displacement_vars', []))
        vector_vars.update(md.get('vector_vars', {}))
    
    # Merge base points
    base_points_list = [md.get('base_points') for md in meshes_data_list if md.get('base_points') is not None]
    base_points = np.vstack(base_points_list) if base_points_list else None
    
    return {
        'mesh': merged_mesh,
        'time_values': time_values,
        'n_times': n_times,
        'point_data_all': point_data_all,
        'cell_data_all': cell_data_all,
        'base_points': base_points,
        'point_vars': sorted(list(point_vars)),
        'cell_vars': sorted(list(cell_vars)),
        'displacement_vars': sorted(list(displacement_vars)),
        'vector_vars': vector_vars
    }

def merge_meshio_meshes(meshes: List[meshio.Mesh]) -> Optional[meshio.Mesh]:
    """Merge meshio Mesh objects (topology only)."""
    if not meshes:
        return None
    if len(meshes) == 1:
        return meshes[0]
    
    all_points = []
    cells_by_type = defaultdict(list)
    offset = 0
    
    for mesh in meshes:
        all_points.append(mesh.points)
        for cell_block in mesh.cells:
            typ = cell_block.type
            shifted_data = cell_block.data + offset
            cells_by_type[typ].append(shifted_data)
        offset += len(mesh.points)
    
    points = np.vstack(all_points)
    cells = []
    for typ in sorted(cells_by_type.keys()):
        data = np.concatenate(cells_by_type[typ], axis=0)
        cells.append(meshio.CellBlock(typ, data))
    
    return meshio.Mesh(points=points, cells=cells)

# -----------------------------------------------------------------------------
# Helper Functions - Surface & Volume Extraction
# -----------------------------------------------------------------------------
# REMOVED @st.cache_data decorator because meshio.Mesh is unhashable
def extract_mesh_surfaces(meshio_mesh: meshio.Mesh, cell_types_filter: Optional[List[str]] = None) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[List[Tuple[int, int]]]]:
    """Extract surface triangles from mesh for Plotly visualization."""
    if meshio_mesh is None:
        return None, None, None
    
    points = meshio_mesh.points
    if points is None or len(points) == 0:
        return None, None, None
    
    faces = []
    face_cell_map = []
    
    if not meshio_mesh.cells:
        return None, None, None
    
    supported_types = ['tetra', 'tetrahedron', 'hexahedron', 'hex', 'hexa', 
                       'triangle', 'tri', 'quad', 'quadrilateral', 
                       'wedge', 'triangular_prism', 'pyramid', 'pyra']
    
    for block_idx, cell_block in enumerate(meshio_mesh.cells):
        if cell_block is None or cell_block.data is None:
            continue
        cell_type = cell_block.type
        cells = cell_block.data
        
        if cells is None or len(cells) == 0:
            continue
        
        if cell_types_filter and cell_type not in cell_types_filter:
            continue
        
        try:
            if cell_type in ['tetra', 'tetrahedron']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 4:
                        tetra_faces = [
                            [cell[0], cell[1], cell[2]],
                            [cell[0], cell[1], cell[3]],
                            [cell[0], cell[2], cell[3]],
                            [cell[1], cell[2], cell[3]]
                        ]
                        for face in tetra_faces:
                            faces.append(face)
                            face_cell_map.append((block_idx, cell_idx))
            
            elif cell_type in ['hexahedron', 'hex', 'hexa', 'hexahedron20', 'hexahedron27']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 8:
                        hex_faces = [
                            [cell[0], cell[1], cell[2], cell[3]],
                            [cell[4], cell[5], cell[6], cell[7]],
                            [cell[0], cell[1], cell[5], cell[4]],
                            [cell[2], cell[3], cell[7], cell[6]],
                            [cell[0], cell[3], cell[7], cell[4]],
                            [cell[1], cell[2], cell[6], cell[5]]
                        ]
                        for quad in hex_faces:
                            faces.append([quad[0], quad[1], quad[2]])
                            faces.append([quad[0], quad[2], quad[3]])
                            face_cell_map.extend([(block_idx, cell_idx), (block_idx, cell_idx)])
            
            elif cell_type in ['triangle', 'tri', 'triangle6', 'triangle7']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 3:
                        faces.append([cell[0], cell[1], cell[2]])
                        face_cell_map.append((block_idx, cell_idx))
            
            elif cell_type in ['quad', 'quadrilateral', 'quad8', 'quad9']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 4:
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[0], cell[2], cell[3]])
                        face_cell_map.extend([(block_idx, cell_idx), (block_idx, cell_idx)])
            
            elif cell_type in ['wedge', 'triangular_prism', 'wedge15', 'wedge18']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 6:
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[3], cell[5], cell[4]])
                        face_cell_map.extend([(block_idx, cell_idx), (block_idx, cell_idx)])
                        wedge_faces = [
                            [cell[0], cell[1], cell[4], cell[3]],
                            [cell[1], cell[2], cell[5], cell[4]],
                            [cell[2], cell[0], cell[3], cell[5]]
                        ]
                        for quad in wedge_faces:
                            faces.append([quad[0], quad[1], quad[2]])
                            faces.append([quad[0], quad[2], quad[3]])
                            face_cell_map.extend([(block_idx, cell_idx), (block_idx, cell_idx)])
            
            elif cell_type in ['pyramid', 'pyra', 'pyramid13']:
                for cell_idx, cell in enumerate(cells):
                    if len(cell) >= 5:
                        faces.append([cell[0], cell[1], cell[2]])
                        faces.append([cell[0], cell[2], cell[3]])
                        face_cell_map.extend([(block_idx, cell_idx), (block_idx, cell_idx)])
                        for tri in [[cell[0], cell[1], cell[4]],
                                   [cell[1], cell[2], cell[4]],
                                   [cell[2], cell[3], cell[4]],
                                   [cell[3], cell[0], cell[4]]]:
                            faces.append(tri)
                            face_cell_map.append((block_idx, cell_idx))
            
            elif cell_type in ['line', 'line2', 'line3', 'vertex']:
                continue
            
            elif cell_type not in supported_types:
                if not hasattr(extract_mesh_surfaces, '_logged_unsupported'):
                    extract_mesh_surfaces._logged_unsupported = set()
                if cell_type not in extract_mesh_surfaces._logged_unsupported:
                    extract_mesh_surfaces._logged_unsupported.add(cell_type)
                    logger.warning(f"Unsupported cell type for surface extraction: {cell_type}")
                    st.warning(f"Cell type '{cell_type}' not fully supported; visualization may be incomplete.")
        
        except (IndexError, TypeError, ValueError, KeyError) as e:
            logger.debug(f"Error processing cell type {cell_type}: {e}")
            continue
    
    if len(faces) == 0:
        logger.warning("No faces extracted from mesh")
        return None, None, None
    
    try:
        faces = np.array(faces, dtype=np.int32)
        if faces.ndim != 2 or faces.shape[1] != 3:
            return None, None, None
        
        # Remove duplicate faces (internal faces)
        sorted_faces = np.sort(faces, axis=1)
        unique_faces, unique_indices = np.unique(sorted_faces, axis=0, return_index=True)
        faces = faces[unique_indices]
        
        logger.info(f"Extracted {len(faces)} surface faces from {len(meshio_mesh.cells)} cell blocks")
        return points, faces, face_cell_map
    except Exception as e:
        logger.error(f"Error processing faces: {e}")
        return None, None, None

# -----------------------------------------------------------------------------
# Helper Functions - Plotly Visualization (Enhanced)
# -----------------------------------------------------------------------------
def create_plotly_mesh(points: np.ndarray, faces: np.ndarray, values: Optional[np.ndarray] = None, 
                       color_map: str = 'Viridis', opacity: float = 0.9, show_edges: bool = False, 
                       title: str = "Mesh", show_scalar_bar: bool = True, 
                       camera_preset: str = 'isometric', vector_data: Optional[np.ndarray] = None, 
                       show_vectors: bool = False, vector_scale: float = 1.0) -> go.Figure:
    """
    Create a Plotly 3D mesh visualization with scalar and vector field support.
    """
    if points is None or faces is None or len(points) == 0 or len(faces) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No mesh data available for visualization",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="gray")
        )
        fig.update_layout(
            scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z', aspectmode='data'),
            height=600, title=title, template='plotly_white'
        )
        return fig
    
    try:
        i, j, k = faces[:, 0], faces[:, 1], faces[:, 2]
    except (IndexError, TypeError):
        return create_plotly_mesh(None, None, None, None, title=title)
    
    traces = []
    
    # Mesh trace with scalar values
    intensity = None
    colorscale = None
    showscale = False
    colorbar = None
    
    if values is not None and len(values) > 0:
        try:
            values_flat = np.asarray(values).flatten()
            if len(values_flat) == len(faces):
                intensity = values_flat
                colorscale = color_map
                showscale = show_scalar_bar
                if show_scalar_bar:
                    colorbar = dict(
                        title=dict(text=title, font=dict(size=11)),
                        thickness=20,
                        len=0.6,
                        x=0.95,
                        y=0.5
                    )
        except Exception as e:
            logger.warning(f"Error applying scalar values: {e}")
    
    mesh_trace = go.Mesh3d(
        x=points[:, 0], y=points[:, 1], z=points[:, 2],
        i=i, j=j, k=k,
        intensity=intensity,
        colorscale=colorscale,
        opacity=opacity,
        showscale=showscale,
        colorbar=colorbar,
        flatshading=True,
        lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.4, specular=0.3),
        lightposition=dict(x=100, y=100, z=100),
        name='Mesh',
        hovertemplate=(
            "<b>Face</b><br>" +
            "X: %{x:.3f}<br>" +
            "Y: %{y:.3f}<br>" +
            "Z: %{z:.3f}<br>" +
            (f"Value: %{{intensity:.4g}}<br>" if intensity is not None else "") +
            "<extra></extra>"
        )
    )
    traces.append(mesh_trace)
    
    # Vector field visualization using Cone trace
    if show_vectors and vector_data is not None and len(vector_data) == len(points):
        try:
            vector_data = np.asarray(vector_data)
            if vector_data.ndim == 2 and vector_data.shape[1] in [2, 3]:
                # Pad 2D vectors to 3D
                if vector_data.shape[1] == 2:
                    vector_data = np.column_stack([vector_data, np.zeros(len(vector_data))])
                
                # Scale vectors for visibility
                u, v, w = vector_data[:, 0] * vector_scale, vector_data[:, 1] * vector_scale, vector_data[:, 2] * vector_scale
                
                # Sample vectors for performance (show every Nth)
                sample_rate = max(1, len(points) // 500)
                if sample_rate > 1:
                    idx = np.arange(0, len(points), sample_rate)
                    cone_trace = go.Cone(
                        x=points[idx, 0], y=points[idx, 1], z=points[idx, 2],
                        u=u[idx], v=v[idx], w=w[idx],
                        sizemode='absolute',
                        sizeref=0.5,
                        anchor='tail',
                        colorscale=color_map,
                        showscale=False,
                        name='Vectors',
                        opacity=0.7
                    )
                else:
                    cone_trace = go.Cone(
                        x=points[:, 0], y=points[:, 1], z=points[:, 2],
                        u=u, v=v, w=w,
                        sizemode='absolute',
                        sizeref=0.5,
                        anchor='tail',
                        colorscale=color_map,
                        showscale=False,
                        name='Vectors',
                        opacity=0.7
                    )
                traces.append(cone_trace)
                logger.info(f"Added vector field visualization with {len(vector_data)} vectors")
        except Exception as e:
            logger.warning(f"Error adding vector visualization: {e}")
            st.warning(f"Could not display vector field: {e}")
    
    # Edge visualization
    if show_edges and len(faces) < 30000:
        edge_x, edge_y, edge_z = [], [], []
        for face in faces:
            for idx1, idx2 in [(0,1), (1,2), (2,0)]:
                try:
                    p1, p2 = points[face[idx1]], points[face[idx2]]
                    edge_x.extend([p1[0], p2[0], None])
                    edge_y.extend([p1[1], p2[1], None])
                    edge_z.extend([p1[2], p2[2], None])
                except (IndexError, TypeError):
                    continue
        if edge_x:
            edge_trace = go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='black', width=0.5),
                name='Edges',
                opacity=0.5,
                showlegend=False,
                hoverinfo='skip'
            )
            traces.append(edge_trace)
    
    fig = go.Figure(data=traces)
    
    # Camera presets
    camera_presets = {
        'isometric': dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        'top': dict(eye=dict(x=0, y=0, z=2.5)),
        'front': dict(eye=dict(x=0, y=2.5, z=0)),
        'side': dict(eye=dict(x=2.5, y=0, z=0)),
        'corner': dict(eye=dict(x=2, y=2, z=1)),
    }
    camera = camera_presets.get(camera_preset, camera_presets['isometric'])
    
    fig.update_layout(
        scene=dict(
            xaxis_title='X', yaxis_title='Y', zaxis_title='Z',
            aspectmode='data',
            camera=camera,
            bgcolor='white'
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=18)),
        hovermode='closest',
        template='plotly_white',
        paper_bgcolor='white',
        plot_bgcolor='white'
    )
    
    return fig

def create_isosurface_plot(points: np.ndarray, cells: List[meshio.CellBlock], 
                          scalar_values: np.ndarray, isovalue: float, 
                          color_map: str = 'Viridis', title: str = "Isosurface") -> Optional[go.Figure]:
    """Create an isosurface plot using Plotly's Isosurface trace."""
    try:
        if scalar_values is None or len(scalar_values) != len(points):
            return None
        
        # Extract tetrahedral cells for isosurface
        tetra_cells = []
        for cell_block in cells:
            if cell_block and cell_block.type in ['tetra', 'tetrahedron'] and cell_block.data is not None:
                tetra_cells.extend(cell_block.data.tolist())
        
        if not tetra_cells:
            logger.warning("Isosurface requires tetrahedral mesh; none found")
            return None
        
        # Flatten cells for Plotly
        x, y, z = points[:, 0], points[:, 1], points[:, 2]
        i, j, k, l = zip(*[(c[0], c[1], c[2], c[3]) for c in tetra_cells])
        
        fig = go.Figure(data=go.Isosurface(
            x=x, y=y, z=z,
            i=i, j=j, k=k, l=l,
            value=scalar_values,
            isomin=isovalue,
            isomax=isovalue,
            colorscale=color_map,
            opacity=0.8,
            surface_count=1,
            showscale=True,
            colorbar=dict(title=dict(text=title, font=dict(size=11))),
            hovertemplate="X: %{x:.3f}<br>Y: %{y:.3f}<br>Z: %{z:.3f}<br>Value: %{value:.4g}<extra></extra>"
        ))
        
        fig.update_layout(
            scene=dict(
                xaxis_title='X', yaxis_title='Y', zaxis_title='Z',
                aspectmode='data'
            ),
            height=600,
            title=dict(text=f"{title} (iso={isovalue:.3g})", x=0.5),
            template='plotly_white'
        )
        return fig
    except Exception as e:
        logger.error(f"Error creating isosurface: {e}")
        return None

def create_variable_histogram(values: np.ndarray, var_name: str, nbins: int = 50) -> Optional[go.Figure]:
    """Create a histogram of variable values."""
    if values is None or len(values) == 0:
        return None
    try:
        values = np.asarray(values).flatten()
        values = values[np.isfinite(values)]
        if len(values) == 0:
            return None
        fig = go.Figure(data=[
            go.Histogram(
                x=values,
                nbinsx=nbins,
                marker_color='#667eea',
                opacity=0.7,
                name=var_name
            )
        ])
        fig.update_layout(
            title=f"Distribution: {var_name}",
            xaxis_title="Value",
            yaxis_title="Count",
            height=300,
            margin=dict(l=40, r=20, t=40, b=40),
            template='plotly_white'
        )
        return fig
    except Exception as e:
        logger.warning(f"Error creating histogram: {e}")
        return None

def create_time_series_plot(mesh_data: Dict[str, Any], variable_base: str, time_step_current: int) -> Optional[go.Figure]:
    """Create a time series plot showing variable evolution over all time steps."""
    if mesh_data is None or variable_base is None:
        return None
    
    point_data_all = mesh_data.get('point_data_all', {})
    cell_data_all = mesh_data.get('cell_data_all', {})
    time_values = mesh_data.get('time_values')
    n_times = mesh_data.get('n_times', 1)
    
    if n_times <= 1:
        return None
    
    # Find the variable data
    data = None
    location = None
    if variable_base in point_data_all:
        data = point_data_all[variable_base]
        location = 'point'
    elif variable_base in cell_data_all:
        data = cell_data_all[variable_base]
        location = 'cell'
    
    if data is None:
        return None
    
    try:
        # Compute statistic per time step
        if data.ndim >= 2:
            time_stats = []
            for t in range(min(n_times, data.shape[0])):
                ts_data = data[t]
                if ts_data.ndim > 1 and ts_data.shape[-1] in [2, 3]:
                    # Vector: compute magnitude
                    ts_data = np.linalg.norm(ts_data, axis=-1)
                time_stats.append({
                    'mean': float(np.mean(ts_data)),
                    'min': float(np.min(ts_data)),
                    'max': float(np.max(ts_data))
                })
            
            if time_values is None:
                time_values = np.arange(n_times)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=time_values[:len(time_stats)],
                y=[s['mean'] for s in time_stats],
                mode='lines+markers',
                name='Mean',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            fig.add_trace(go.Scatter(
                x=time_values[:len(time_stats)],
                y=[s['max'] for s in time_stats],
                mode='lines',
                name='Max',
                line=dict(color='#d62728', width=1, dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=time_values[:len(time_stats)],
                y=[s['min'] for s in time_stats],
                mode='lines',
                name='Min',
                line=dict(color='#2ca02c', width=1, dash='dash')
            ))
            
            # Mark current time step
            current_time = time_values[time_step_current] if time_step_current < len(time_values) else time_step_current
            fig.add_vline(x=current_time, line_dash="dot", line_color="gray",
                         annotation_text=f"Current: t={current_time:.3g}")
            
            fig.update_layout(
                title=f"Time Evolution: {variable_base}",
                xaxis_title="Time" if time_values is not None else "Time Step",
                yaxis_title="Value",
                height=300,
                margin=dict(l=40, r=20, t=40, b=40),
                template='plotly_white',
                hovermode='x unified'
            )
            return fig
    except Exception as e:
        logger.warning(f"Error creating time series: {e}")
    
    return None

# -----------------------------------------------------------------------------
# Helper Functions - Format Conversion for ParaView
# -----------------------------------------------------------------------------
def get_meshio_write_formats() -> set:
    """Dynamically get supported write formats from meshio."""
    try:
        import meshio
        if hasattr(meshio, '_format_registry'):
            return set(meshio._format_registry.write.keys())
        elif hasattr(meshio, 'extension_to_filetype'):
            return set(meshio.extension_to_filetype.values())
        else:
            return {'vtu', 'vtk', 'stl', 'ply', 'xdmf', 'exodus'}
    except Exception as e:
        logger.warning(f"Error getting meshio formats: {e}")
        return {'vtu', 'vtk', 'stl', 'ply', 'xdmf', 'exodus'}

def convert_mesh_format(mesh_data: Dict[str, Any], output_path: str, file_format: str, 
                       time_step: int = 0, export_all_times: bool = False) -> Tuple[bool, str, float]:
    """
    Convert mesh to specified format using meshio.
    Supports single timestep or full time series export.
    """
    if mesh_data is None:
        return False, "No mesh data to export", 0
    
    mesh = mesh_data.get('mesh')
    if mesh is None:
        return False, "No mesh topology available", 0
    
    supported = get_meshio_write_formats()
    if file_format not in supported:
        return False, f"Format '{file_format}' not supported. Available: {sorted(supported)}", 0
    
    if file_format not in SUPPORTED_EXPORT_FORMATS:
        return False, f"Unknown format: {file_format}", 0
    
    format_info = SUPPORTED_EXPORT_FORMATS[file_format]
    
    # Check dependencies
    if 'requires' in format_info:
        for dep in format_info['requires']:
            try:
                __import__(dep)
            except ImportError:
                return False, f"{format_info['name']} requires '{dep}': pip install {dep}", 0
    
    try:
        if export_all_times and format_info.get('supports_timeseries', False):
            # Export full time series
            n_times = mesh_data.get('n_times', 1)
            time_values = mesh_data.get('time_values')
            point_data_all = mesh_data.get('point_data_all', {})
            cell_data_all = mesh_data.get('cell_data_all', {})
            
            if file_format == 'xdmf':
                # XDMF + HDF5 for time series
                import h5py
                h5_path = output_path.replace('.xdmf', '.h5')
                
                with h5py.File(h5_path, 'w') as h5f:
                    # Write mesh topology once
                    points_ds = h5f.create_dataset('Points', data=mesh.points)
                    cells_group = h5f.create_group('Cells')
                    for i, cell_block in enumerate(mesh.cells):
                        if cell_block and cell_block.data is not None:
                            cells_group.create_dataset(f'cell_{i}', data=cell_block.data)
                
                # Write XDMF wrapper
                with open(output_path, 'w') as xdmf:
                    xdmf.write('<?xml version="1.0" ?>\n<!DOCTYPE Xdmf SYSTEM "Xdmf.dtd" []>\n<Xdmf Version="3.0">\n  <Domain>\n')
                    xdmf.write(f'    <Grid Name="TimeSeries" GridType="Collection" CollectionType="Temporal">\n')
                    for t in range(n_times):
                        xdmf.write(f'      <Grid Name="Step_{t}" GridType="Uniform">\n')
                        xdmf.write(f'        <Time Value="{time_values[t] if time_values is not None and t < len(time_values) else t}"/>\n')
                        xdmf.write(f'        <Topology Type="Mixed" NumberOfElements="{mesh_data.get("n_cells", 0)}">\n')
                        xdmf.write(f'          <DataItem Format="HDF" Dimensions="{len(mesh.points)} 3">{h5_path}:/Points</DataItem>\n')
                        xdmf.write(f'        </Topology>\n')
                        xdmf.write(f'      </Grid>\n')
                    xdmf.write('    </Grid>\n  </Domain>\n</Xdmf>')
                
                size_mb = get_file_size_mb(output_path) + get_file_size_mb(h5_path)
                return True, f"Exported time series: {format_file_size(size_mb)}", size_mb
            
            elif file_format in ['vtu', 'exodus']:
                # Export as series of files
                base_path = output_path.rsplit('.', 1)[0]
                for t in range(n_times):
                    t_path = f"{base_path}_t{t:04d}{format_info['ext']}"
                    success, msg, _ = convert_mesh_format(mesh_data, t_path, file_format, time_step=t, export_all_times=False)
                    if not success:
                        return False, f"Failed at timestep {t}: {msg}", 0
                
                # Write PVD collection file for VTU
                if file_format == 'vtu':
                    pvd_path = f"{base_path}.pvd"
                    with open(pvd_path, 'w') as pvd:
                        pvd.write('<?xml version="1.0"?>\n<VTKFile type="Collection" version="0.1">\n  <Collection>\n')
                        for t in range(n_times):
                            t_val = time_values[t] if time_values is not None and t < len(time_values) else t
                            pvd.write(f'    <DataSet timestep="{t_val}" group="" part="0" file="{os.path.basename(f"{base_path}_t{t:04d}.vtu")}"/>\n')
                        pvd.write('  </Collection>\n</VTKFile>')
                
                return True, f"Exported {n_times} timesteps", get_file_size_mb(output_path)
        
        else:
            # Single timestep export
            export_mesh = meshio.Mesh(
                points=mesh.points,
                cells=mesh.cells
            )
            
            # Add point data for selected time step
            point_data_all = mesh_data.get('point_data_all', {})
            for var_name, data in point_data_all.items():
                try:
                    if data.ndim >= 2 and time_step < data.shape[0]:
                        export_mesh.point_data[var_name] = data[time_step]
                    elif data.ndim == 1:
                        export_mesh.point_data[var_name] = data
                except Exception as e:
                    logger.debug(f"Skipping point var {var_name}: {e}")
                    continue
            
            # Add cell data for selected time step
            cell_data_all = mesh_data.get('cell_data_all', {})
            for var_name, data in cell_data_all.items():
                try:
                    if data.ndim >= 2 and time_step < data.shape[0]:
                        export_mesh.cell_data[var_name] = [data[time_step]]
                    elif data.ndim == 1:
                        export_mesh.cell_data[var_name] = [data]
                except Exception as e:
                    logger.debug(f"Skipping cell var {var_name}: {e}")
                    continue
            
            # Surface-only export if needed
            if format_info.get('surface_only', False):
                points, faces, _ = extract_mesh_surfaces(mesh)
                if points is None or faces is None or len(faces) == 0:
                    return False, "Could not extract surface mesh", 0
                triangle_cells = meshio.CellBlock('triangle', faces)
                export_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
                
                # Filter point data for PLY
                if file_format == 'ply' and export_mesh.point_data:
                    scalar_point_data = {}
                    for key, val in export_mesh.point_data.items():
                        try:
                            arr = np.asarray(val)
                            if arr.ndim == 1 or (arr.ndim == 2 and arr.shape[1] <= 3):
                                scalar_point_data[key] = arr
                        except Exception:
                            continue
                    if scalar_point_data:
                        export_mesh.point_data = scalar_point_data
            
            meshio.write(output_path, export_mesh, file_format=file_format)
            
            if os.path.exists(output_path):
                size_mb = get_file_size_mb(output_path)
                if size_mb > 0:
                    return True, f"Exported: {format_file_size(size_mb)}", size_mb
                return False, "Output file is empty", 0
            return False, "Failed to create output file", 0
    
    except ImportError as e:
        logger.error(f"Import error during export: {e}")
        return False, f"Missing dependency: {e}", 0
    except Exception as e:
        logger.error(f"Export error: {type(e).__name__}: {e}")
        return False, f"{type(e).__name__}: {str(e)[:200]}", 0

def export_variable_csv(mesh_data: Dict[str, Any], variable_base: str, output_path: str, time_step: int = 0) -> Tuple[bool, str]:
    """Export variable data to CSV with coordinates for the specified timestep."""
    if mesh_data is None or not variable_base:
        return False, "No data to export"
    
    try:
        mesh = mesh_data.get('mesh')
        if mesh is None:
            return False, "No mesh available"
        
        point_data_all = mesh_data.get('point_data_all', {})
        cell_data_all = mesh_data.get('cell_data_all', {})
        
        # Determine location and get data
        location = None
        data = None
        
        if variable_base in point_data_all:
            data = point_data_all[variable_base]
            location = 'point'
        elif variable_base in cell_data_all:
            data = cell_data_all[variable_base]
            location = 'cell'
        
        if data is None:
            return False, f"Variable '{variable_base}' not found"
        
        # Extract time step
        if data.ndim >= 2 and time_step < data.shape[0]:
            data = data[time_step]
        
        # Handle vector data
        if data.ndim > 1 and data.shape[1] <= 3:
            df = pd.DataFrame(data, columns=[f'{variable_base}_{i}' for i in range(data.shape[1])])
            df[f'{variable_base}_mag'] = np.linalg.norm(data, axis=1)
        elif data.ndim > 1:
            df = pd.DataFrame(data)
            df.columns = [f'{variable_base}_{i}' for i in range(data.shape[1])]
        else:
            df = pd.DataFrame({variable_base: data})
        
        # Add coordinates for point data
        if location == 'point' and mesh.points is not None:
            coord_df = pd.DataFrame(mesh.points[:, :3], columns=['x', 'y', 'z'])
            df = pd.concat([coord_df, df], axis=1)
        
        df.insert(0, 'index', range(len(df)))
        df.to_csv(output_path, index=False)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, f"Exported {len(df)} rows"
        return False, "Empty output"
    
    except ImportError:
        return False, "pandas required: pip install pandas"
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        return False, f"{type(e).__name__}: {e}"

# -----------------------------------------------------------------------------
# Helper Functions - Data Processing
# -----------------------------------------------------------------------------
def get_variable_values(mesh_data: Dict[str, Any], variable_base: str, faces: Optional[np.ndarray] = None, 
                       face_cell_map: Optional[List[Tuple[int, int]]] = None, time_step: int = 0, 
                       return_vector: bool = False) -> Optional[np.ndarray]:
    """
    Extract scalar or vector values for a variable at a given timestep.
    If faces provided and location is point, maps to faces.
    If return_vector=True and data is vector, returns full vector array.
    """
    if variable_base is None or mesh_data is None:
        return None
    
    point_data_all = mesh_data.get('point_data_all', {})
    cell_data_all = mesh_data.get('cell_data_all', {})
    mesh = mesh_data.get('mesh')
    
    # Determine location and get data
    location = None
    data = None
    
    if variable_base in point_data_all:
        data = point_data_all[variable_base]
        location = 'point'
    elif variable_base in cell_data_all:
        data = cell_data_all[variable_base]
        location = 'cell'
    
    if data is None:
        return None
    
    # Extract time step
    if data.ndim >= 2 and time_step < data.shape[0]:
        data = data[time_step]
    elif data.ndim >= 2:
        data = data[-1]
    
    # Return vector if requested and data is vector
    if return_vector and data.ndim > 1 and data.shape[-1] in [2, 3]:
        return data
    
    # Convert to scalar (magnitude for vectors)
    if data.ndim > 1 and data.shape[-1] in [2, 3]:
        data = np.linalg.norm(data, axis=-1)
    
    # Map to faces if requested and point data
    if location == 'point' and faces is not None and len(faces) > 0:
        try:
            face_values = np.mean(data[faces], axis=1)
            return face_values
        except (IndexError, TypeError, ValueError) as e:
            logger.warning(f"Error mapping point values to faces: {e}")
            return None
    
    return data

def apply_deformation(mesh_data: Dict[str, Any], time_step: int) -> Optional[np.ndarray]:
    """
    Apply displacement to base points for deforming mesh visualization.
    Returns deformed points array or None if not deforming.
    """
    if not mesh_data:
        return None
    
    base_points = mesh_data.get('base_points')
    if base_points is None:
        return None
    
    displacement_vars = mesh_data.get('displacement_vars', [])
    if len(displacement_vars) < 2:  # Need at least x and y
        return None
    
    point_data_all = mesh_data.get('point_data_all', {})
    n_points = len(base_points)
    
    # Get displacement components
    disp_x = point_data_all.get('disp_x', point_data_all.get('displacement_x'))
    disp_y = point_data_all.get('disp_y', point_data_all.get('displacement_y'))
    disp_z = point_data_all.get('disp_z', point_data_all.get('displacement_z'))
    
    if disp_x is None or disp_y is None:
        return None
    
    # Extract time step
    ts_idx = min(time_step, disp_x.shape[0] - 1)
    
    # Build displacement vector
    disp = np.zeros((n_points, 3))
    disp[:, 0] = disp_x[ts_idx] if disp_x.ndim >= 2 else disp_x
    disp[:, 1] = disp_y[ts_idx] if disp_y.ndim >= 2 else disp_y
    if disp_z is not None:
        disp[:, 2] = disp_z[ts_idx] if disp_z.ndim >= 2 else disp_z
    
    # Apply to base points
    deformed_points = base_points + disp
    logger.info(f"Applied deformation for timestep {time_step}")
    return deformed_points

# -----------------------------------------------------------------------------
# PyVista Integration for Advanced Volume Rendering (Optional)
# -----------------------------------------------------------------------------
def try_import_pyvista():
    """Try to import pyvista for advanced rendering."""
    try:
        import pyvista as pv
        return pv
    except ImportError:
        logger.info("PyVista not installed; volume rendering disabled")
        return None

def create_pyvista_volume(mesh_data: Dict[str, Any], variable_base: str, time_step: int, isovalue: Optional[float] = None):
    """Create a PyVista volume/isosurface plot (requires pyvista)."""
    pv = try_import_pyvista()
    if pv is None or mesh_data is None:
        return None
    
    try:
        mesh = mesh_data.get('mesh')
        if mesh is None:
            return None
        
        # Convert meshio mesh to PyVista UnstructuredGrid
        grid = pv.UnstructuredGrid(
            {
                'faceoffsets': None,
                'face': None,
                'cells': np.concatenate([
                    np.concatenate([[len(c)], c]) for cblock in mesh.cells 
                    for c in cblock.data
                ]) if mesh.cells else None,
                'cell_types': np.array([
                    pv.CellType.TETRA if cblock.type in ['tetra', 'tetrahedron'] 
                    else pv.CellType.HEXAHEDRON if cblock.type in ['hexahedron', 'hex']
                    else pv.CellType.TRIANGLE if cblock.type in ['triangle', 'tri']
                    else pv.CellType.QUAD if cblock.type in ['quad', 'quadrilateral']
                    else pv.CellType.POLYGON
                    for cblock in mesh.cells for _ in range(len(cblock.data))
                ]) if mesh.cells else None
            },
            mesh.points
        )
        
        # Add scalar data
        point_data_all = mesh_data.get('point_data_all', {})
        if variable_base in point_data_all:
            data = point_data_all[variable_base]
            if data.ndim >= 2 and time_step < data.shape[0]:
                data = data[time_step]
            if data.ndim > 1 and data.shape[-1] in [2, 3]:
                data = np.linalg.norm(data, axis=-1)
            grid.point_data[variable_base] = data
        
        plotter = pv.Plotter(off_screen=True)
        
        if isovalue is not None:
            # Isosurface
            plotter.add_mesh(grid.contour([isovalue], scalars=variable_base), 
                           scalars=variable_base, cmap='viridis')
        else:
            # Volume rendering
            plotter.add_volume(grid, scalars=variable_base, cmap='viridis', opacity='linear')
        
        # Return as image for Streamlit
        img = plotter.screenshot(return_img=True)
        plotter.close()
        return img
    
    except Exception as e:
        logger.error(f"PyVista rendering error: {e}")
        return None

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    """Main application entry point."""
    st.markdown('<div class="main-header">🦌 MOOSE Exodus Viewer Pro</div>', unsafe_allow_html=True)
    st.markdown("""
    **Visualize** MOOSE simulation results with full variable & field support.
    **Time-Series**: Interactive sliders for all timesteps.
    **Deforming Meshes**: Support for displacement variables.
    **Vector Fields**: Cone/streamline visualization.
    **Volume Rendering**: Isosurfaces and volumetric views (PyVista).
    **Export**: ParaView-compatible formats with time-series support.
    """)
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(app_dir, "dataset")
    
    # Initialize session state
    state_keys = [
        'selected_dir', 'mesh_data', 'mesh_stats', 'cache_dir',
        'points', 'faces', 'face_cell_map', 'current_time_step',
        'visualization_mode', 'vector_scale', 'isosurface_value',
        'show_vectors', 'enable_volume', 'deformation_applied'
    ]
    for key in state_keys:
        if key not in st.session_state:
            st.session_state[key] = None if key not in ['current_time_step', 'vector_scale', 'isosurface_value'] else 0
    
    if 'cache_dir' not in st.session_state:
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="moose_viewer_pro_")
    
    # Clear cache button
    if st.sidebar.button("🗑️ Clear Cache", help="Clear loaded mesh data"):
        for key in ['mesh_data', 'mesh_stats', 'points', 'faces', 'face_cell_map',
                   'selected_dir', 'current_time_step', 'visualization_mode']:
            st.session_state[key] = None
        st.rerun()
    
    with st.sidebar:
        st.header("1. Select Simulation")
        
        # Find subdirectories
        if not os.path.exists(dataset_dir):
            os.makedirs(dataset_dir, exist_ok=True)
            st.warning(f"Created 'dataset/' directory. Place Exodus files in subdirectories.")
            st.stop()
        
        subdirs = [d for d in sorted(os.listdir(dataset_dir))
                  if os.path.isdir(os.path.join(dataset_dir, d)) and not d.startswith('.')]
        
        if not subdirs:
            st.warning("No subdirectories found in 'dataset/' folder.")
            st.markdown(f"""
            **Setup:** Create `{dataset_dir}/your_case/` and place Exodus files there.
            """)
            st.stop()
        
        selected_subdir = st.selectbox("Choose Case", subdirs, key="subdir_select")
        selected_dir = os.path.join(dataset_dir, selected_subdir)
        
        exodus_files = find_exodus_files(selected_dir, recursive=False)
        
        if not exodus_files:
            st.warning(f"No Exodus files found in '{selected_subdir}'")
            st.stop()
        else:
            st.success(f"Found {len(exodus_files)} file(s)")
        
        # Load mesh if directory changed or not loaded
        if exodus_files and (st.session_state.selected_dir != selected_dir or st.session_state.mesh_data is None):
            st.session_state.selected_dir = selected_dir
            st.session_state.mesh_data = None
            for key in ['mesh_stats', 'points', 'faces', 'face_cell_map', 'current_time_step']:
                st.session_state[key] = None
            
            meshes_data = []
            with st.spinner(f"Loading {len(exodus_files)} file(s)..."):
                for file_path in sorted(exodus_files):
                    # First read metadata to check time steps
                    metadata = read_exodus_metadata(file_path)
                    if metadata:
                        logger.info(f"Metadata for {file_path}: {metadata['n_times']} timesteps")
                    
                    # Load data (lazy loading - only current timestep initially)
                    mesh_data = load_exodus_data(file_path, time_step=0)
                    if mesh_data:
                        meshes_data.append(mesh_data)
            
            if meshes_data:
                if len(meshes_data) == 1:
                    merged_data = meshes_data[0]
                else:
                    merged_data = merge_meshes(meshes_data)
                
                if merged_data:
                    st.session_state.mesh_data = merged_data
                    
                    # Extract surface geometry
                    mesh = merged_data.get('mesh')
                    if mesh:
                        points, faces, face_cell_map = extract_mesh_surfaces(mesh)
                        st.session_state.points = points
                        st.session_state.faces = faces
                        st.session_state.face_cell_map = face_cell_map
                    
                    # Analyze mesh
                    st.session_state.mesh_stats = analyze_mesh(merged_data, time_step=0)
                    st.session_state.current_time_step = 0
                    
                    st.rerun()
        
        # Time controls
        st.divider()
        st.header("⏱️ Time Controls")
        
        mesh_data = st.session_state.mesh_data
        n_times = 1
        time_values = None
        
        if mesh_data:
            n_times = mesh_data.get('n_times', 1)
            time_values = mesh_data.get('time_values')
        
        if n_times > 1:
            time_step = st.slider(
                "Timestep",
                0, n_times - 1,
                st.session_state.get('current_time_step', n_times - 1),
                key="time_slider"
            )
            st.session_state.current_time_step = time_step
            
            if time_values is not None and len(time_values) >= n_times:
                st.caption(f"Time = {time_values[time_step]:.6g}")
            else:
                st.caption(f"Step {time_step + 1} of {n_times}")
            
            # Animation controls
            col_anim1, col_anim2, col_anim3 = st.columns(3)
            with col_anim1:
                if st.button("⏮️", key="btn_first", help="First timestep"):
                    st.session_state.current_time_step = 0
                    st.rerun()
            with col_anim2:
                if st.button("⏹️", key="btn_play", help="Auto-play"):
                    st.session_state.setdefault('autoplay', False)
                    st.session_state.autoplay = not st.session_state.autoplay
            with col_anim3:
                if st.button("⏭️", key="btn_last", help="Last timestep"):
                    st.session_state.current_time_step = n_times - 1
                    st.rerun()
            
            if st.session_state.get('autoplay', False):
                sleep_time = st.slider("Speed", 0.1, 2.0, 0.5, key="speed")
                import time
                time.sleep(sleep_time)
                st.session_state.current_time_step = (st.session_state.current_time_step + 1) % n_times
                st.rerun()
        else:
            time_step = 0
            st.info("Static mesh")
        
        # Visualization mode toggles
        st.divider()
        st.header("🎨 Visualization Mode")
        
        viz_mode = st.radio(
            "Render Mode",
            ["Surface", "Isosurface", "Volume (PyVista)"],
            key="viz_mode",
            horizontal=True
        )
        st.session_state.visualization_mode = viz_mode
        
        if viz_mode == "Isosurface":
            stats = st.session_state.mesh_stats or {}
            var_info = stats.get('field_info', {}).get(st.session_state.get('selected_variable'), {})
            var_range = var_info.get('range', (0, 1))
            iso_val = st.slider("Isosurface Value", 
                               float(var_range[0]), float(var_range[1]), 
                               (var_range[0] + var_range[1]) / 2,
                               key="iso_slider")
            st.session_state.isosurface_value = iso_val
        
        if viz_mode == "Volume (PyVista)":
            pv_available = try_import_pyvista() is not None
            if not pv_available:
                st.warning("PyVista not installed. Install with: `pip install pyvista`")
            st.session_state.enable_volume = pv_available
    
    # Main visualization area
    st.divider()
    st.header("2. Visualization Controls")
    
    col_vis1, col_vis2, col_vis3, col_vis4 = st.columns(4)
    with col_vis1:
        color_map = st.selectbox(
            "Color Scale",
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis",
             "Jet", "Rainbow", "Portland", "Turbo", "Spectral"],
            key="colormap"
        )
    with col_vis2:
        opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05, key="opacity")
    with col_vis3:
        show_edges = st.checkbox("Edges", value=False, key="show_edges")
        show_scalar_bar = st.checkbox("Color Bar", value=True, key="show_scalar_bar")
    with col_vis4:
        camera_preset = st.selectbox(
            "View",
            ["isometric", "top", "front", "side", "corner"],
            key="camera_preset"
        )
    
    st.divider()
    
    # Info section
    st.header("📊 Mesh Information")
    
    if mesh_data and st.session_state.mesh_stats:
        stats = st.session_state.mesh_stats
        points = st.session_state.points
        faces = st.session_state.faces
        face_cell_map = st.session_state.face_cell_map
        time_step = st.session_state.current_time_step
        
        # Update stats for current time step
        stats = analyze_mesh(mesh_data, time_step=time_step)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats.get('n_points', 0):,}</div>
                <div class="metric-label">Points</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats.get('n_cells', 0):,}</div>
                <div class="metric-label">Cells</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats.get('n_times', 1)}</div>
                <div class="metric-label">Timesteps</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            point_vars = stats.get('point_vars', [])
            cell_vars = stats.get('cell_vars', [])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(point_vars) + len(cell_vars)}</div>
                <div class="metric-label">Variables</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Variable selection
        col_var1, col_var2 = st.columns([3, 1])
        with col_var1:
            all_bases = stats.get('point_vars', []) + stats.get('cell_vars', [])
            if not all_bases:
                st.info("No variables found. Visualizing geometry only.")
                variable_base = None
            else:
                variable_base = st.selectbox(
                    "Select Variable",
                    all_bases,
                    key="var_select",
                    index=0,
                    help="Choose a field to visualize"
                )
                st.session_state.selected_variable = variable_base
        with col_var2:
            if variable_base and variable_base in stats.get('field_info', {}):
                info = stats['field_info'][variable_base]
                range_val = info.get('range')
                if range_val:
                    st.metric("Range", f"{range_val[0]:.3g} to {range_val[1]:.3g}")
        
        # Vector field options
        if variable_base and stats.get('field_info', {}).get(variable_base, {}).get('is_vector', False):
            st.divider()
            st.subheader("🔷 Vector Field Options")
            col_vec1, col_vec2, col_vec3 = st.columns(3)
            with col_vec1:
                show_vectors = st.checkbox("Show Vectors", value=False, key="show_vectors")
                st.session_state.show_vectors = show_vectors
            with col_vec2:
                vector_scale = st.slider("Vector Scale", 0.01, 10.0, 1.0, key="vec_scale")
                st.session_state.vector_scale = vector_scale
            with col_vec3:
                vec_mode = st.selectbox("Display", ["Magnitude", "Components"], key="vec_mode")
        
        # Deforming mesh support
        if stats.get('is_deforming', False):
            st.info(f"🔄 Deforming mesh detected. Applying displacement for timestep {time_step}.")
            # Apply deformation to points
            deformed_points = apply_deformation(mesh_data, time_step)
            if deformed_points is not None:
                points = deformed_points
                st.session_state.deformation_applied = True
        
        # Extract values for current time step
        values = None
        vector_data = None
        
        if variable_base and faces is not None and len(faces) > 0:
            # Get scalar values for surface
            values = get_variable_values(
                mesh_data, variable_base, faces, face_cell_map,
                time_step=time_step, return_vector=False
            )
            # Get vector data if needed
            if stats.get('field_info', {}).get(variable_base, {}).get('is_vector', False) and st.session_state.get('show_vectors', False):
                vector_data = get_variable_values(
                    mesh_data, variable_base, None, None,
                    time_step=time_step, return_vector=True
                )
        
        # Create visualization based on mode
        fig = None
        
        if points is not None and faces is not None and len(points) > 0 and len(faces) > 0:
            time_label = ""
            if time_values is not None and len(time_values) > time_step:
                time_label = f" (t={time_values[time_step]:.6g})"
            else:
                time_label = f" (Step {time_step + 1}/{stats.get('n_times', 1)})"
            
            viz_mode = st.session_state.get('visualization_mode', 'Surface')
            
            if viz_mode == "Surface":
                fig = create_plotly_mesh(
                    points, faces, values,
                    color_map=color_map,
                    opacity=opacity,
                    show_edges=show_edges,
                    title=f"{variable_base or 'Geometry'}{time_label}",
                    show_scalar_bar=show_scalar_bar,
                    camera_preset=camera_preset,
                    vector_data=vector_data if st.session_state.get('show_vectors') else None,
                    show_vectors=st.session_state.get('show_vectors', False),
                    vector_scale=st.session_state.get('vector_scale', 1.0)
                )
            
            elif viz_mode == "Isosurface":
                # Get full point data for isosurface
                scalar_values = get_variable_values(
                    mesh_data, variable_base, None, None,
                    time_step=time_step, return_vector=False
                )
                if scalar_values is not None and len(scalar_values) == len(points):
                    iso_val = st.session_state.get('isosurface_value', 0)
                    fig = create_isosurface_plot(
                        points, mesh_data.get('mesh').cells if mesh_data.get('mesh') else [],
                        scalar_values, iso_val, color_map,
                        title=f"{variable_base} Isosurface{time_label}"
                    )
                if fig is None:
                    st.warning("Isosurface requires tetrahedral mesh and scalar data")
                    # FIX: Use explicit title instead of undefined variable
                    fig = create_plotly_mesh(points, faces, values, color_map=color_map, title=f"{variable_base or 'Geometry'} (fallback){time_label}")
            
            elif viz_mode == "Volume (PyVista)":
                if try_import_pyvista():
                    with st.spinner("Rendering volume (may take time)..."):
                        img = create_pyvista_volume(
                            mesh_data, variable_base, time_step,
                            isovalue=st.session_state.get('isosurface_value') if viz_mode == "Isosurface" else None
                        )
                        if img is not None:
                            st.image(img, caption=f"{variable_base} Volume{time_label}", use_container_width=True)
                        else:
                            st.warning("Volume rendering failed; falling back to surface")
                            fig = create_plotly_mesh(points, faces, values, color_map=color_map, title=f"{variable_base or 'Geometry'}{time_label}")
                else:
                    st.warning("Install PyVista for volume rendering: `pip install pyvista`")
                    fig = create_plotly_mesh(points, faces, values, color_map=color_map, title=f"{variable_base or 'Geometry'}{time_label}")
            
            if fig is not None:
                st.divider()
                st.subheader("🎨 3D Visualization")
                st.plotly_chart(fig, use_container_width=True, key="plotly_viz")
                
                # Variable distribution histogram
                if values is not None and len(values) > 0 and viz_mode == "Surface":
                    with st.expander("📈 Variable Distribution", expanded=False):
                        hist_fig = create_variable_histogram(values, variable_base)
                        if hist_fig:
                            st.plotly_chart(hist_fig, use_container_width=True)
                
                # Time series plot
                if stats.get('n_times', 1) > 1 and variable_base:
                    with st.expander("📉 Time Evolution", expanded=False):
                        ts_fig = create_time_series_plot(mesh_data, variable_base, time_step)
                        if ts_fig:
                            st.plotly_chart(ts_fig, use_container_width=True)
        else:
            st.warning("Could not extract mesh surfaces")
            st.markdown("""
            **Try:** Download and open in ParaView for full mesh support.
            """)
        
        # Export section
        st.divider()
        st.subheader("📤 Export for ParaView")
        
        with st.expander("Mesh Details", expanded=False):
            st.write(f"**Directory:** `{selected_subdir}`")
            st.write(f"**Files:** {len(exodus_files)}")
            st.write(f"**Points:** {stats.get('n_points', 0):,}")
            st.write(f"**Cells:** {stats.get('n_cells', 0):,}")
            st.write(f"**Timesteps:** {stats.get('n_times', 1)}")
            if time_values is not None:
                st.write(f"**Time Range:** {time_values[0]:.6g} to {time_values[-1]:.6g}")
            if stats.get('cell_types'):
                st.write("**Cell Types:**")
                for ctype, count in stats['cell_types'].items():
                    st.write(f" - `{ctype}`: {count:,}")
            if stats.get('is_deforming'):
                st.success("✅ Deforming mesh support enabled")
            if stats.get('vector_vars'):
                st.write("**Vector Fields:**")
                for var, meta in stats['vector_vars'].items():
                    st.write(f" - `{var}` ({meta['location']}, {meta['components']} components)")
        
        st.markdown("### Available Formats")
        available_formats = {k: v for k, v in SUPPORTED_EXPORT_FORMATS.items()
                           if k in get_meshio_write_formats()}
        
        if not available_formats:
            st.warning("No export formats available. Check meshio installation.")
        else:
            # Time series export option
            export_all = st.checkbox("Export all timesteps (time series)", key="export_all_times", 
                                    help="Only available for VTU, XDMF, Exodus formats")
            
            cols = st.columns(min(len(available_formats), 6))
            for idx, (fmt_key, fmt_info) in enumerate(available_formats.items()):
                with cols[idx % len(cols)]:
                    export_filename = f"mesh_output_t{time_step}{fmt_info['ext']}" if not export_all else f"mesh_series{fmt_info['ext']}"
                    export_path = os.path.join(st.session_state.cache_dir, export_filename)
                    
                    can_export_timeseries = fmt_info.get('supports_timeseries', False) and export_all
                    
                    success, message, file_size = convert_mesh_format(
                        mesh_data, export_path, fmt_key, 
                        time_step=time_step, 
                        export_all_times=can_export_timeseries
                    )
                    
                    if success and os.path.exists(export_path):
                        with open(export_path, 'rb') as f:
                            file_bytes = f.read()
                        st.download_button(
                            label=f"{fmt_info['name']}",
                            data=file_bytes,
                            file_name=export_filename,
                            mime=fmt_info['mime'],
                            key=f"download_{fmt_key}",
                            help=f"{fmt_info['desc']}\nSize: {format_file_size(file_size)}",
                            type="primary" if fmt_key == 'vtu' else "secondary"
                        )
                    else:
                        st.button(
                            label=f"Unavailable: {fmt_info['name']}",
                            disabled=True,
                            key=f"download_{fmt_key}_disabled",
                            help=f"Unavailable: {message}"
                        )
                    st.caption(fmt_info['desc'].split('(')[0].strip())
        
        with st.expander("Format Comparison Guide", expanded=False):
            st.markdown("""
            | Format | Best For | ParaView | Variables | Time Series | Size |
            |--------|----------|----------|-----------|-------------|------|
            | **VTU** | Full 3D analysis | Excellent | All | ✅ (with PVD) | Medium |
            | **VTK** | Legacy compatibility | Good | All | ❌ | Large |
            | **PLY** | Surface visualization | Limited | Point only | ❌ | Small |
            | **STL** | 3D printing/CAD | Geometry only | None | ❌ | Small |
            | **XDMF** | Large/parallel data | Excellent | All | ✅ | Small |
            | **Exodus** | MOOSE re-import | Native | All | ✅ | Medium |
            """)
        
        st.info("""
        **Recommendation:**
        - Use **VTU + PVD** for time-series animations in ParaView
        - Use **PLY** for quick surface previews
        - Use **CSV** (below) for data analysis in Excel/Python
        """)
        
        # CSV Export
        if variable_base:
            st.markdown("### 📊 Export Variable Data (CSV)")
            csv_filename = f"{variable_base}_t{time_step}_data.csv"
            csv_path = os.path.join(st.session_state.cache_dir, csv_filename)
            csv_success, csv_msg = export_variable_csv(
                mesh_data, variable_base, csv_path, time_step=time_step
            )
            if csv_success and os.path.exists(csv_path):
                with open(csv_path, 'rb') as f:
                    csv_bytes = f.read()
                col_csv1, col_csv2 = st.columns([3, 1])
                with col_csv1:
                    st.download_button(
                        label=f"Download {csv_filename}",
                        data=csv_bytes,
                        file_name=csv_filename,
                        mime="text/csv",
                        key="download_csv",
                        help="Variable values with point coordinates"
                    )
                with col_csv2:
                    try:
                        row_count = pd.read_csv(csv_path).shape[0]
                        st.metric("Rows", f"{row_count:,}")
                    except Exception:
                        st.metric("Rows", "Unknown")
            else:
                st.button("CSV Export Unavailable", disabled=True, help=csv_msg)
        
        st.info("""
        **ParaView Import Guide:**
        1. Download `.vtu` file (or `.pvd` for time series)
        2. Open ParaView → File → Open → Select file
        3. Click "Apply" in Properties panel
        4. Use "Color By" to select variables
        5. Click "Rescale to Data Range" for proper colors
        6. For time series: Use the time slider in ParaView toolbar
        """)
    
    else:
        if mesh_data is None:
            st.error("Failed to load mesh. Check file format and dependencies.")
            with st.expander("Troubleshooting"):
                st.markdown("""
                **Common Issues:**
                - Missing `netCDF4`: Install with `pip install netCDF4`
                - Missing `h5py` for HDF5-based Exodus: `pip install h5py`
                - File not in Exodus format: Ensure it's a MOOSE output file
                - Permission issues: Check file/directory permissions
                """)
        else:
            st.warning("No variable data found. The mesh might be empty or have no data.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: gray; padding: 1rem;">
    <small>
    MOOSE Exodus Viewer Pro v4.0 |
    Built with Streamlit + Plotly + Meshio + NetCDF4 + PyVista |
    <a href="https://mooseframework.inl.gov" target="_blank">MOOSE Framework</a>
    </small>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
