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
from typing import List, Tuple, Optional, Dict, Any

warnings.filterwarnings('ignore')

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MOOSE Exodus Viewer",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://mooseframework.inl.gov',
        'Report a bug': 'https://github.com/idaholab/moose/issues',
        'About': "MOOSE Exodus Viewer v3.0\nBuilt with Streamlit + Plotly + Meshio"
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
        'surface_only': False
    },
    'vtk': {
        'name': 'VTK (Legacy)',
        'ext': '.vtk',
        'mime': 'text/plain',
        'desc': 'Legacy VTK format (widely compatible)',
        'surface_only': False
    },
    'stl': {
        'name': 'STL (Surface)',
        'ext': '.stl',
        'mime': 'application/sla',
        'desc': 'Surface mesh for CAD/3D printing (no scalar data)',
        'surface_only': True
    },
    'ply': {
        'name': 'PLY (Polygon)',
        'ext': '.ply',
        'mime': 'application/octet-stream',
        'desc': 'Surface with vertex colors/data (good for visualization)',
        'surface_only': True
    },
    'xdmf': {
        'name': 'XDMF (Large Data)',
        'ext': '.xdmf',
        'mime': 'application/xml',
        'desc': 'XDMF for large datasets (requires h5py)',
        'surface_only': False,
        'requires': ['h5py']
    },
    'exodus': {
        'name': 'Exodus (MOOSE Native)',
        'ext': '.e',
        'mime': 'application/octet-stream',
        'desc': 'Native MOOSE format (for re-import)',
        'surface_only': False
    },
}

# -----------------------------------------------------------------------------
# Helper Functions - Part File Discovery (NEW)
# -----------------------------------------------------------------------------
def is_part_file(file_path: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """
    Check if a file is a part file based on naming pattern.
    
    Returns:
        tuple: (is_part: bool, base_path: str, part_number: int or None)
    """
    path = Path(file_path)
    name = path.name
    
    # Pattern 1: file.e.part1
    match = re.match(r'^(.+)\.part(\d+)$', name)
    if match:
        base_name = match.group(1)
        part_num = int(match.group(2))
        return True, str(path.parent / base_name), part_num
    
    # Pattern 2: file.e.1
    match = re.match(r'^(.+)\.(\d+)$', name)
    if match:
        base_name = match.group(1)
        part_num = int(match.group(2))
        return True, str(path.parent / base_name), part_num
    
    # Pattern 3: file.e-s001 (MOOSE parallel output)
    match = re.match(r'^(.+)-s(\d+)$', name)
    if match:
        base_name = match.group(1)
        part_num = int(match.group(2))
        return True, str(path.parent / base_name), part_num
    
    return False, str(file_path), None

def find_exodus_part_files(base_path: str, extension: str = '.e', max_parts: int = 1000) -> List[str]:
    """
    Find all part files for a given base Exodus file.
    Looks for patterns like: file.e.part1, file.e.part2, ...
    or file.e.1, file.e.2, ...
    
    Args:
        base_path: Base file path (e.g., /path/to/file.e)
        extension: File extension (default: '.e')
        max_parts: Maximum number of parts to search for
    
    Returns:
        list: Sorted list of part file paths
    """
    base = Path(base_path)
    part_files = []
    
    # Pattern 1: file.e.part1, file.e.part2, ...
    for i in range(1, max_parts + 1):
        part_file = base.parent / f"{base.name}.part{i}"
        if part_file.exists():
            part_files.append(str(part_file))
        else:
            # Check if there's a gap (missing part)
            if i > 1:
                break
    
    # Pattern 2: file.e.1, file.e.2, ... (if no .part files found)
    if not part_files:
        for i in range(1, max_parts + 1):
            part_file = base.parent / f"{base.name}.{i}"
            if part_file.exists():
                part_files.append(str(part_file))
            else:
                if i > 1:
                    break
    
    # Pattern 3: file.e-s001, file.e-s002, ... (MOOSE parallel output)
    if not part_files:
        for i in range(1, max_parts + 1):
            part_file = base.parent / f"{base.name}-s{i:03d}"
            if part_file.exists():
                part_files.append(str(part_file))
            else:
                if i > 1:
                    break
    
    return part_files

def combine_meshes(meshes: List[meshio.Mesh]) -> Optional[meshio.Mesh]:
    """
    Combine multiple meshio mesh objects into one.
    
    Args:
        meshes: List of meshio.Mesh objects
    
    Returns:
        Combined meshio.Mesh object
    """
    if not meshes:
        return None
    
    if len(meshes) == 1:
        return meshes[0]
    
    # Combine points
    all_points = []
    point_offsets = [0]
    
    for mesh in meshes:
        if mesh.points is not None:
            all_points.append(mesh.points)
            point_offsets.append(point_offsets[-1] + len(mesh.points))
    
    if not all_points:
        return None
    
    combined_points = np.vstack(all_points)
    
    # Combine cells (adjust indices for point offsets)
    combined_cells = []
    cell_types_seen = {}
    
    for mesh_idx, mesh in enumerate(meshes):
        if not mesh.cells:
            continue
        
        offset = point_offsets[mesh_idx]
        
        for cell_block in mesh.cells:
            if cell_block is None or cell_block.data is None:
                continue
            
            cell_type = cell_block.type
            cells = cell_block.data + offset  # Adjust point indices
            
            if cell_type in cell_types_seen:
                cell_types_seen[cell_type].append(cells)
            else:
                cell_types_seen[cell_type] = [cells]
    
    # Create combined cell blocks
    for cell_type, cell_lists in cell_types_seen.items():
        combined_cell_data = np.vstack(cell_lists)
        combined_cells.append(meshio.CellBlock(cell_type, combined_cell_data))
    
    # Combine point data
    combined_point_data = {}
    for mesh in meshes:
        if mesh.point_data:
            for key, value in mesh.point_data.items():
                if key in combined_point_data:
                    combined_point_data[key] = np.vstack([combined_point_data[key], value])
                else:
                    combined_point_data[key] = value
    
    # Combine cell data
    combined_cell_data = {}
    for mesh in meshes:
        if mesh.cell_data:
            for key, blocks in mesh.cell_data.items():
                if key in combined_cell_data:
                    combined_cell_data[key].extend(blocks)
                else:
                    combined_cell_data[key] = list(blocks)
    
    return meshio.Mesh(
        points=combined_points,
        cells=combined_cells,
        point_data=combined_point_data if combined_point_data else None,
        cell_data=combined_cell_data if combined_cell_data else None
    )

def get_combined_file_size(part_files: List[str]) -> float:
    """Get total size of all part files in MB."""
    total_size = 0
    for part_file in part_files:
        try:
            total_size += os.path.getsize(part_file)
        except OSError:
            pass
    return total_size / (1024 * 1024)

# -----------------------------------------------------------------------------
# Helper Functions - File Discovery (UPDATED)
# -----------------------------------------------------------------------------
def find_exodus_files(search_dir, recursive=True):
    """
    Recursively find all Exodus files in the given directory.
    Now includes detection of part files and groups them.
    
    Args:
        search_dir: Directory path to search
        recursive: Whether to search subdirectories
    
    Returns:
        list: Sorted list of file paths (base files, with parts detected)
    """
    exodus_extensions = ['.e', '.exo', '.exodus', '.out', '.ex2']
    exodus_files = []
    part_file_groups = {}  # base_path -> [part_files]
    
    if not os.path.exists(search_dir):
        return exodus_files
    
    try:
        if recursive:
            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.git']]
                for file in files:
                    if file.startswith('.'):
                        continue
                    file_ext = os.path.splitext(file)[1].lower()
                    full_path = os.path.join(root, file)
                    
                    # Check if this is a part file
                    is_part, base_path, part_num = is_part_file(full_path)
                    if is_part:
                        if base_path not in part_file_groups:
                            part_file_groups[base_path] = []
                        part_file_groups[base_path].append((part_num, full_path))
                    elif file_ext in exodus_extensions or re.match(r'\.e-s\d+$', file_ext):
                        exodus_files.append(full_path)
        else:
            for file in os.listdir(search_dir):
                if file.startswith('.'):
                    continue
                file_ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(search_dir, file)
                
                is_part, base_path, part_num = is_part_file(full_path)
                if is_part:
                    if base_path not in part_file_groups:
                        part_file_groups[base_path] = []
                    part_file_groups[base_path].append((part_num, full_path))
                elif file_ext in exodus_extensions:
                    exodus_files.append(full_path)
    except PermissionError as e:
        st.warning(f"Permission denied accessing: {search_dir}")
    except Exception as e:
        st.warning(f"Error scanning directory: {e}")
    
    # Add base paths for part file groups
    for base_path, parts in part_file_groups.items():
        parts.sort(key=lambda x: x[0])  # Sort by part number
        exodus_files.append(base_path)  # Add base path representation
    
    exodus_files.sort(key=lambda x: (os.path.dirname(x), os.path.basename(x).lower()))
    return exodus_files

def get_file_display_name(file_path, base_dir):
    """Creates a user-friendly display name showing relative path and part info."""
    try:
        rel_path = os.path.relpath(file_path, base_dir)
        
        # Check if this is a base path for part files
        part_files = find_exodus_part_files(file_path)
        if part_files:
            part_count = len(part_files)
            total_size = get_combined_file_size(part_files)
            if os.path.dirname(rel_path):
                return f"📁 {rel_path} ({part_count} parts, {format_file_size(total_size)})"
            return f"📄 {os.path.basename(file_path)} ({part_count} parts, {format_file_size(total_size)})"
        
        if os.path.dirname(rel_path):
            return f"📁 {rel_path}"
        return f"📄 {os.path.basename(file_path)}"
    except ValueError:
        return f"📄 {os.path.basename(file_path)}"
    except Exception:
        return os.path.basename(file_path)

def get_file_size_mb(file_path):
    """Get file size in MB with error handling. Includes part files."""
    try:
        # Check for part files
        part_files = find_exodus_part_files(file_path)
        if part_files:
            return get_combined_file_size(part_files)
        
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0

def format_file_size(size_mb):
    """Format file size with appropriate units."""
    if size_mb < 1:
        return f"{size_mb * 1024:.1f} KB"
    elif size_mb < 100:
        return f"{size_mb:.2f} MB"
    else:
        return f"{size_mb:.1f} MB"

# -----------------------------------------------------------------------------
# Helper Functions - Mesh Loading & Analysis (UPDATED)
# -----------------------------------------------------------------------------
def load_exodus_data(file_path, time_step=None):
    """
    Reads an Exodus file using meshio.
    Now supports reading and combining part files.
    
    Args:
        file_path: Path to Exodus file (or base path for parts)
        time_step: Optional time step index to load (for multi-step files)
    
    Returns:
        meshio mesh object or None on error
    """
    # Check for part files
    part_files = []
    part_files = find_exodus_part_files(file_path)
    
    files_to_load = part_files if part_files else [file_path]
    
    # Verify files exist
    for f in files_to_load:
        if not os.path.exists(f):
            st.error(f"File not found: {f}")
            return None
    
    try:
        if len(files_to_load) == 1:
            # Single file (no parts)
            with st.spinner(f"Reading {os.path.basename(files_to_load[0])}..."):
                mesh = meshio.read(files_to_load[0])
        else:
            # Multiple part files - combine them
            with st.spinner(f"Reading {len(files_to_load)} part files..."):
                meshes = []
                progress_bar = st.progress(0)
                
                for idx, part_file in enumerate(files_to_load):
                    part_mesh = meshio.read(part_file)
                    if part_mesh and part_mesh.points is not None:
                        meshes.append(part_mesh)
                    progress_bar.progress((idx + 1) / len(files_to_load))
                
                if not meshes:
                    st.error("No valid mesh data found in part files")
                    return None
                
                # Combine meshes
                mesh = combine_meshes(meshes)
                progress_bar.empty()
                st.success(f"Combined {len(files_to_load)} part files successfully")
        
        if mesh.points is None or len(mesh.points) == 0:
            st.warning("Mesh has no points. File may be empty or corrupted.")
            return None
        
        if not mesh.cells or all(c.data is None or len(c.data) == 0 for c in mesh.cells):
            st.warning("Mesh has no cells. Cannot visualize topology.")
            return mesh
        
        return mesh
        
    except ImportError as e:
        error_msg = str(e).lower()
        if 'netcdf' in error_msg or 'netcdf4' in error_msg:
            st.error("Missing NetCDF support for Exodus files")
            st.info("Install with: `pip install netCDF4` or `conda install -c conda-forge netcdf4`")
        elif 'h5py' in error_msg:
            st.error("Missing h5py for HDF5-based Exodus files")
            st.info("Install with: `pip install h5py`")
        else:
            st.error(f"Missing dependency: {e}")
        return None
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if 'NC_' in error_msg or 'NetCDF' in error_msg:
            st.error(f"NetCDF error: {error_msg}")
            st.info("Try: `pip install --upgrade netCDF4`")
        elif 'HDF5' in error_msg or 'hdf5' in error_msg.lower():
            st.error(f"HDF5 error: {error_msg}")
            st.info("Try: `pip install h5py` or check file integrity")
        elif 'format' in error_msg.lower() or 'magic' in error_msg.lower():
            st.error(f"File format error: {error_msg}")
            st.info("Ensure this is a valid MOOSE Exodus output file")
        else:
            st.error(f"Error reading file ({error_type}): {error_msg}")
        with st.expander("Technical Details", expanded=False):
            st.code(f"File: {file_path}\nError: {error_type}: {error_msg}", language="text")
        return None

def analyze_mesh(meshio_mesh):
    """
    Analyze mesh and return statistics dictionary.
    Returns:
        dict: Mesh statistics and metadata
    """
    if meshio_mesh is None:
        return {}
    stats = {
        'n_points': len(meshio_mesh.points) if meshio_mesh.points is not None else 0,
        'n_cells': 0,
        'cell_types': {},
        'dimensions': None,
        'bounds': None,
        'point_vars': [],
        'cell_vars': [],
        'field_info': {}
    }
    if meshio_mesh.cells:
        for cell_block in meshio_mesh.cells:
            if cell_block and cell_block.data is not None:
                cell_type = cell_block.type or 'unknown'
                n_cells = len(cell_block.data)
                stats['n_cells'] += n_cells
                stats['cell_types'][cell_type] = stats['cell_types'].get(cell_type, 0) + n_cells
    if meshio_mesh.points is not None and len(meshio_mesh.points) > 0:
        points = np.asarray(meshio_mesh.points)
        stats['dimensions'] = points.shape[1] if points.ndim > 1 else 1
        stats['bounds'] = {
            'x': (float(np.min(points[:, 0])), float(np.max(points[:, 0]))),
            'y': (float(np.min(points[:, 1])), float(np.max(points[:, 1]))) if points.shape[1] > 1 else None,
            'z': (float(np.min(points[:, 2])), float(np.max(points[:, 2]))) if points.shape[1] > 2 else None,
        }
    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
    for var_name, var_data in point_data.items():
        if var_name and isinstance(var_name, str):
            try:
                arr = np.asarray(var_data)
                stats['point_vars'].append(var_name)
                stats['field_info'][var_name] = {
                    'location': 'point',
                    'shape': arr.shape[1:] if arr.ndim > 1 else (),
                    'dtype': str(arr.dtype),
                    'range': (float(np.min(arr)), float(np.max(arr))) if arr.size > 0 else None
                }
            except Exception:
                stats['point_vars'].append(var_name)
    for var_name, var_data in cell_data.items():
        if var_name and isinstance(var_name, str):
            try:
                if isinstance(var_data, list):
                    arrays = [np.asarray(a) for a in var_data if a is not None]
                    if arrays:
                        arr = arrays[0]
                        stats['cell_vars'].append(var_name)
                        stats['field_info'][var_name] = {
                            'location': 'cell',
                            'shape': arr.shape[1:] if arr.ndim > 1 else (),
                            'dtype': str(arr.dtype),
                            'range': (float(np.min(arr)), float(np.max(arr))) if arr.size > 0 else None
                        }
                else:
                    arr = np.asarray(var_data)
                    stats['cell_vars'].append(var_name)
                    stats['field_info'][var_name] = {
                        'location': 'cell',
                        'shape': arr.shape[1:] if arr.ndim > 1 else (),
                        'dtype': str(arr.dtype),
                        'range': (float(np.min(arr)), float(np.max(arr))) if arr.size > 0 else None
                    }
            except Exception:
                stats['cell_vars'].append(var_name)
    return stats

# -----------------------------------------------------------------------------
# Helper Functions - Surface Extraction for Plotly
# -----------------------------------------------------------------------------
def extract_mesh_surfaces(meshio_mesh, cell_types_filter=None):
    """
    Extract surface triangles from mesh for Plotly visualization.
    Args:
        meshio_mesh: meshio Mesh object
        cell_types_filter: Optional list of cell types to include
    Returns:
        tuple: (points, faces, face_cell_map) or (None, None, None)
    """
    if meshio_mesh is None:
        return None, None, None
    points = meshio_mesh.points
    if points is None or len(points) == 0:
        return None, None, None
    faces = []
    face_cell_map = []
    if not meshio_mesh.cells:
        return None, None, None
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
            else:
                if not hasattr(extract_mesh_surfaces, '_logged_types'):
                    extract_mesh_surfaces._logged_types = set()
                if cell_type not in extract_mesh_surfaces._logged_types:
                    extract_mesh_surfaces._logged_types.add(cell_type)
        except (IndexError, TypeError, ValueError, KeyError) as e:
            continue
    if len(faces) == 0:
        return None, None, None
    try:
        faces = np.array(faces, dtype=np.int32)
        if faces.ndim != 2 or faces.shape[1] != 3:
            return None, None, None
        sorted_faces = np.sort(faces, axis=1)
        unique_faces, unique_indices = np.unique(sorted_faces, axis=0, return_index=True)
        faces = faces[unique_indices]
        return points, faces, face_cell_map
    except Exception as e:
        return None, None, None

# -----------------------------------------------------------------------------
# Helper Functions - Plotly Visualization
# -----------------------------------------------------------------------------
def create_plotly_mesh(points, faces, values=None, color_map='Viridis',
                       opacity=0.9, show_edges=False, title="Mesh",
                       show_scalar_bar=True, camera_preset='isometric'):
    """
    Create a Plotly 3D mesh visualization with extensive customization.
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
                        title=dict(text=title, font=dict(size=11)),
                        thickness=20,
                        len=0.6,
                        x=0.95,
                        y=0.5
                    )
        except Exception:
            pass
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
    fig = go.Figure(data=[mesh_trace])
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
            fig.add_trace(go.Scatter3d(
                x=edge_x, y=edge_y, z=edge_z,
                mode='lines',
                line=dict(color='black', width=0.5),
                name='Edges',
                opacity=0.5,
                showlegend=False,
                hoverinfo='skip'
            ))
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

def create_variable_histogram(values, var_name, nbins=50):
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
    except Exception:
        return None

# -----------------------------------------------------------------------------
# Helper Functions - Format Conversion for ParaView
# -----------------------------------------------------------------------------
def get_meshio_write_formats():
    """
    Dynamically get supported write formats from meshio.
    Returns set of format keys.
    """
    try:
        import meshio
        if hasattr(meshio, '_format_registry'):
            return set(meshio._format_registry.write.keys())
        elif hasattr(meshio, 'extension_to_filetype'):
            return set(meshio.extension_to_filetype.values())
        else:
            return {'vtu', 'vtk', 'stl', 'ply', 'xdmf', 'exodus'}
    except Exception:
        return {'vtu', 'vtk', 'stl', 'ply', 'xdmf', 'exodus'}

def convert_mesh_format(meshio_mesh, output_path, file_format):
    """
    Convert mesh to specified format using meshio.
    Returns:
        tuple: (success: bool, message: str, file_size_mb: float)
    """
    if meshio_mesh is None:
        return False, "No mesh data to export", 0
    supported = get_meshio_write_formats()
    if file_format not in supported:
        return False, f"Format '{file_format}' not supported by meshio. Available: {sorted(supported)}", 0
    if file_format not in SUPPORTED_EXPORT_FORMATS:
        return False, f"Unknown format configuration: {file_format}", 0
    format_info = SUPPORTED_EXPORT_FORMATS[file_format]
    if 'requires' in format_info:
        for dep in format_info['requires']:
            try:
                __import__(dep)
            except ImportError:
                return False, f"{format_info['name']} requires '{dep}': pip install {dep}", 0
    try:
        if format_info.get('surface_only', False):
            points, faces, _ = extract_mesh_surfaces(meshio_mesh)
            if points is None or faces is None or len(faces) == 0:
                return False, "Could not extract surface mesh for export", 0
            triangle_cells = meshio.CellBlock('triangle', faces)
            export_mesh = meshio.Mesh(points=points, cells=[triangle_cells])
            if file_format == 'ply' and hasattr(meshio_mesh, 'point_data') and meshio_mesh.point_data:
                scalar_point_data = {}
                for key, val in meshio_mesh.point_data.items():
                    try:
                        arr = np.asarray(val)
                        if arr.ndim == 1 or (arr.ndim == 2 and arr.shape[1] <= 3):
                            scalar_point_data[key] = arr
                    except Exception:
                        continue
                if scalar_point_data:
                    export_mesh.point_data = scalar_point_data
        else:
            export_mesh = meshio_mesh
        meshio.write(output_path, export_mesh, file_format=file_format)
        if os.path.exists(output_path):
            size_mb = get_file_size_mb(output_path)
            if size_mb > 0:
                return True, f"Exported: {format_file_size(size_mb)}", size_mb
            return False, "Output file is empty", 0
        return False, "Failed to create output file", 0
    except ImportError as e:
        return False, f"Missing dependency: {e}", 0
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}", 0

def export_variable_csv(meshio_mesh, variable_name, output_path):
    """Export variable data to CSV with coordinates."""
    if meshio_mesh is None or not variable_name:
        return False, "No data to export"
    try:
        import pandas as pd
        point_data = getattr(meshio_mesh, 'point_data', None) or {}
        cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
        if variable_name in point_data:
            data = np.asarray(point_data[variable_name])
            location = 'point'
            coords = meshio_mesh.points
        elif variable_name in cell_data:
            cdata = cell_data[variable_name]
            if isinstance(cdata, list):
                data = np.concatenate([np.asarray(a) for a in cdata if a is not None])
            else:
                data = np.asarray(cdata)
            location = 'cell'
            coords = None
        else:
            return False, f"Variable '{variable_name}' not found in mesh"
        if data.ndim > 1:
            if data.shape[1] <= 3:
                df = pd.DataFrame(data, columns=[f'{variable_name}_{i}' for i in range(data.shape[1])])
                df[f'{variable_name}_mag'] = np.linalg.norm(data, axis=1)
            else:
                df = pd.DataFrame(data)
                df.columns = [f'{variable_name}_{i}' for i in range(data.shape[1])]
        else:
            df = pd.DataFrame({variable_name: data})
        if location == 'point' and coords is not None:
            coord_df = pd.DataFrame(coords[:, :3], columns=['x', 'y', 'z'])
            df = pd.concat([coord_df, df], axis=1)
        df.insert(0, 'index', range(len(df)))
        df.to_csv(output_path, index=False)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, f"Exported {len(df)} rows"
        return False, "Empty output"
    except ImportError:
        return False, "pandas required: pip install pandas"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# -----------------------------------------------------------------------------
# Helper Functions - Data Processing
# -----------------------------------------------------------------------------
def get_variable_values(meshio_mesh, variable_name, faces, face_cell_map=None):
    """
    Extract scalar values for a variable, mapped to faces.
    Returns:
        numpy array of face values or None
    """
    if variable_name is None or faces is None or len(faces) == 0:
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
        except (IndexError, TypeError, ValueError):
            return None
    elif variable_name in cell_data:
        cell_values = cell_data[variable_name]
        if cell_values is None:
            return None
        if isinstance(cell_values, list):
            arrays = [np.asarray(a) for a in cell_values if a is not None]
            if not arrays:
                return None
            cell_values = np.concatenate(arrays)
        else:
            cell_values = np.asarray(cell_values)
        if cell_values.ndim > 1 and cell_values.shape[1] > 1:
            cell_values = np.linalg.norm(cell_values, axis=1)
        if face_cell_map and len(face_cell_map) == len(faces):
            face_values = np.zeros(len(faces))
            for face_idx, (block_idx, cell_idx) in enumerate(face_cell_map):
                global_idx = 0
                for bi, cb in enumerate(meshio_mesh.cells):
                    if cb and cb.data is not None:
                        if bi < block_idx:
                            global_idx += len(cb.data)
                        elif bi == block_idx:
                            global_idx += cell_idx
                            break
                if 0 <= global_idx < len(cell_values):
                    face_values[face_idx] = cell_values[global_idx]
            return face_values
        total_cells = sum(len(cb.data) for cb in meshio_mesh.cells if cb and cb.data is not None)
        if total_cells > 0 and len(cell_values) == total_cells:
            faces_per_cell = max(1, len(faces) // total_cells)
            face_values = np.repeat(cell_values, faces_per_cell)
            if len(face_values) > len(faces):
                face_values = face_values[:len(faces)]
            elif len(face_values) < len(faces):
                face_values = np.pad(face_values, (0, len(faces) - len(face_values)), mode='edge')
            return face_values
        return None
    return None

def get_available_variables(meshio_mesh):
    """Get list of available variables with metadata."""
    if meshio_mesh is None:
        return [], [], []
    point_data = getattr(meshio_mesh, 'point_data', None) or {}
    cell_data = getattr(meshio_mesh, 'cell_data', None) or {}
    point_vars = sorted([v for v in point_data.keys() if v and isinstance(v, str)])
    cell_vars = sorted([v for v in cell_data.keys() if v and isinstance(v, str)])
    return point_vars, cell_vars, point_vars + cell_vars

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    """Main application entry point."""
    st.markdown('<div class="main-header">🦌 MOOSE Exodus Output Viewer</div>', unsafe_allow_html=True)
    st.markdown("""
    **Visualize** MOOSE simulation results interactively in your browser.
    **Download** in ParaView-compatible formats for advanced post-processing.
    """)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(app_dir, "dataset")
    if 'selected_file_path' not in st.session_state:
        st.session_state.selected_file_path = None
    if 'meshio_mesh' not in st.session_state:
        st.session_state.meshio_mesh = None
    if 'mesh_stats' not in st.session_state:
        st.session_state.mesh_stats = None
    if 'cache_dir' not in st.session_state:
        st.session_state.cache_dir = tempfile.mkdtemp(prefix="moose_viewer_")
    if 'points' not in st.session_state:
        st.session_state.points = None
    if 'faces' not in st.session_state:
        st.session_state.faces = None
    if 'face_cell_map' not in st.session_state:
        st.session_state.face_cell_map = None
    if st.sidebar.button("Clear Cache", help="Clear loaded mesh data"):
        for key in ['meshio_mesh', 'mesh_stats', 'points', 'faces', 'face_cell_map']:
            st.session_state[key] = None
        st.rerun()
    with st.sidebar:
        st.header("1. Select File")
        exodus_files = find_exodus_files(dataset_dir)
        source_option = st.radio(
            "File Source",
            ["Dataset Folder", "Upload File"],
            key="source_radio",
            horizontal=False
        )
        selected_file_path = None
        if source_option == "Dataset Folder":
            if exodus_files:
                st.success(f"Found {len(exodus_files)} file(s)")
                file_options = {get_file_display_name(f, app_dir): f for f in exodus_files}
                selected_display = st.selectbox(
                    "Choose Exodus File",
                    list(file_options.keys()),
                    key="file_select",
                    index=0
                )
                selected_file_path = file_options[selected_display]
                size_mb = get_file_size_mb(selected_file_path)
                st.markdown(f"""
                <div class="success-box">
                <strong>{os.path.basename(selected_file_path)}</strong><br>
                Size: {format_file_size(size_mb)}<br>
                <small>{selected_file_path}</small>
                </div>
                """, unsafe_allow_html=True)
                
                # Show Part File Details if applicable
                part_files = find_exodus_part_files(selected_file_path)
                if part_files:
                    with st.expander(f"📦 Part Files ({len(part_files)} parts)", expanded=True):
                        st.markdown("**Part File Details:**")
                        total_size = 0
                        for idx, part_file in enumerate(part_files, 1):
                            try:
                                size = os.path.getsize(part_file) / (1024 * 1024)
                                total_size += size
                                st.markdown(f"`{idx}. {os.path.basename(part_file)}` - {format_file_size(size)}")
                            except OSError:
                                st.markdown(f"`{idx}. {os.path.basename(part_file)}` - Size unknown")
                        st.markdown(f"**Total Size:** {format_file_size(total_size)}")
            else:
                st.warning("No Exodus files in `dataset/`")
                st.markdown(f"""
                **Create folder:** `{dataset_dir}`
                **Supported:** `.e`, `.exo`, `.exodus`, `.out`, `.ex2`
                **Parts:** `.e.part1`, `.e.1`, `.e-s001`
                """)
        else:
            uploaded_file = st.file_uploader(
                "Upload Exodus File",
                type=['e', 'exo', 'exodus', 'out', 'ex2'],
                key="file_uploader"
            )
            if uploaded_file:
                tmp_path = os.path.join(st.session_state.cache_dir, uploaded_file.name)
                with open(tmp_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                selected_file_path = tmp_path
                size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.markdown(f"""
                <div class="success-box">
                <strong>{uploaded_file.name}</strong><br>
                Size: {format_file_size(size_mb)}
                </div>
                """, unsafe_allow_html=True)
        st.divider()
        st.header("2. Visualization")
        color_map = st.selectbox(
            "Color Scale",
            ["Viridis", "Plasma", "Inferno", "Magma", "Cividis",
             "Jet", "Rainbow", "Portland", "Turbo", "Spectral"],
            key="colormap"
        )
        opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05, key="opacity")
        show_edges = st.checkbox("Show Edges", value=False, key="show_edges")
        show_scalar_bar = st.checkbox("Show Color Bar", value=True, key="show_scalar_bar")
        camera_preset = st.selectbox(
            "Camera View",
            ["isometric", "top", "front", "side", "corner"],
            key="camera_preset"
        )
        st.divider()
        st.header("Info")
        st.markdown("""
        **MOOSE Exodus Viewer v3.0**
        Streamlit + Plotly + Meshio
        ParaView-compatible exports
        No VTK compilation needed
        **Exports:** VTU, VTK, STL, PLY, XDMF, CSV
        """)
    if selected_file_path:
        if (st.session_state.selected_file_path != selected_file_path or
                st.session_state.meshio_mesh is None):
            st.session_state.selected_file_path = selected_file_path
            st.session_state.meshio_mesh = None
            st.session_state.mesh_stats = None
            st.session_state.points = None
            st.session_state.faces = None
            meshio_mesh = load_exodus_data(selected_file_path)
            if meshio_mesh:
                st.session_state.meshio_mesh = meshio_mesh
                st.session_state.mesh_stats = analyze_mesh(meshio_mesh)
                st.session_state.points, st.session_state.faces, st.session_state.face_cell_map = extract_mesh_surfaces(meshio_mesh)
                st.rerun()
        else:
            meshio_mesh = st.session_state.meshio_mesh
            if meshio_mesh:
                stats = st.session_state.mesh_stats or analyze_mesh(meshio_mesh)
                points = st.session_state.points
                faces = st.session_state.faces
                face_cell_map = st.session_state.face_cell_map
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
                    cell_types = stats.get('cell_types', {})
                    st.markdown(f"""
                    <div class="metric-card">
                    <div class="metric-value">{len(cell_types)}</div>
                    <div class="metric-label">Cell Types</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col4:
                    all_vars = stats.get('point_vars', []) + stats.get('cell_vars', [])
                    st.markdown(f"""
                    <div class="metric-card">
                    <div class="metric-value">{len(all_vars)}</div>
                    <div class="metric-label">Variables</div>
                    </div>
                    """, unsafe_allow_html=True)
                point_vars, cell_vars, all_vars = get_available_variables(meshio_mesh)
                col_var1, col_var2 = st.columns([3, 1])
                with col_var1:
                    if not all_vars:
                        st.info("No variables found. Visualizing geometry only.")
                        variable_name = None
                    else:
                        variable_name = st.selectbox(
                            "Select Variable",
                            all_vars,
                            key="var_select",
                            index=0,
                            help="Choose a field to visualize"
                        )
                with col_var2:
                    if variable_name and variable_name in stats.get('field_info', {}):
                        info = stats['field_info'][variable_name]
                        range_val = info.get('range')
                        if range_val:
                            st.metric("Range", f"{range_val[0]:.3g} to {range_val[1]:.3g}")
                values = None
                if variable_name and faces is not None and len(faces) > 0:
                    values = get_variable_values(meshio_mesh, variable_name, faces, face_cell_map)
                if points is not None and faces is not None and len(points) > 0 and len(faces) > 0:
                    fig = create_plotly_mesh(
                        points, faces, values,
                        color_map=color_map,
                        opacity=opacity,
                        show_edges=show_edges,
                        title=variable_name or "Mesh Geometry",
                        show_scalar_bar=show_scalar_bar,
                        camera_preset=camera_preset
                    )
                    st.divider()
                    st.subheader("3D Visualization")
                    st.plotly_chart(fig, use_container_width=True, key="plotly_viz")
                    if values is not None and len(values) > 0:
                        with st.expander("Variable Distribution", expanded=False):
                            hist_fig = create_variable_histogram(values, variable_name)
                            if hist_fig:
                                st.plotly_chart(hist_fig, use_container_width=True)
                else:
                    st.warning("Could not extract mesh surfaces")
                    st.markdown("""
                    **Try:** Download and open in ParaView for full mesh support.
                    """)
                st.divider()
                st.subheader("Export for ParaView")
                with st.expander("Mesh Details", expanded=False):
                    st.write(f"**File:** `{os.path.basename(selected_file_path)}`")
                    st.write(f"**Points:** {stats.get('n_points', 0):,}")
                    st.write(f"**Cells:** {stats.get('n_cells', 0):,}")
                    if stats.get('cell_types'):
                        st.write("**Cell Types:**")
                        for ctype, count in stats['cell_types'].items():
                            st.write(f"  - `{ctype}`: {count:,}")
                    if stats.get('point_vars'):
                        st.write("**Point Variables:**")
                        for var in stats['point_vars']:
                            info = stats.get('field_info', {}).get(var, {})
                            st.write(f"  - `{var}` {info.get('shape', '')} {info.get('dtype', '')}")
                    if stats.get('cell_vars'):
                        st.write("**Cell Variables:**")
                        for var in stats['cell_vars']:
                            info = stats.get('field_info', {}).get(var, {})
                            st.write(f"  - `{var}` {info.get('shape', '')} {info.get('dtype', '')}")
                st.markdown("### Available Formats")
                available_formats = {k: v for k, v in SUPPORTED_EXPORT_FORMATS.items()
                                     if k in get_meshio_write_formats()}
                if not available_formats:
                    st.warning("No export formats available. Check meshio installation.")
                else:
                    cols = st.columns(min(len(available_formats), 6))
                    for idx, (fmt_key, fmt_info) in enumerate(available_formats.items()):
                        with cols[idx % len(cols)]:
                            export_filename = f"mesh_output{fmt_info['ext']}"
                            export_path = os.path.join(st.session_state.cache_dir, export_filename)
                            success, message, file_size = convert_mesh_format(
                                meshio_mesh, export_path, fmt_key
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
                    | Format | Best For | ParaView | Variables | Size |
                    |--------|----------|----------|-----------|------|
                    | **VTU** | Full 3D analysis | Excellent | All | Medium |
                    | **VTK** | Legacy compatibility | Good | All | Large |
                    | **PLY** | Surface visualization | Limited | Point only | Small |
                    | **STL** | 3D printing/CAD | Geometry only | None | Small |
                    | **XDMF** | Large/parallel data | Excellent | All | Small |
                    | **Exodus** | MOOSE re-import | Native | All | Medium |
                    """)
                st.info("""
                **Recommendation:**
                - Use **VTU** for most ParaView workflows
                - Use **PLY** for quick surface previews
                - Use **CSV** (below) for data analysis in Excel/Python
                """)
                if variable_name:
                    st.markdown("### Export Variable Data (CSV)")
                    csv_filename = f"{variable_name}_data.csv"
                    csv_path = os.path.join(st.session_state.cache_dir, csv_filename)
                    csv_success, csv_msg = export_variable_csv(meshio_mesh, variable_name, csv_path)
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
                1. Download `.vtu` file (recommended for full 3D mesh)
                2. Open ParaView → File → Open → Select file
                3. Click "Apply" in Properties panel
                4. Use "Color By" to select variables
                5. Click "Rescale to Data Range" for proper colors
                """)
            else:
                st.error("Failed to load mesh. Check file format and dependencies.")
    else:
        st.info("Select or upload an Exodus file to begin")
        with st.expander("Getting Started"):
            st.markdown("""
            ### Folder Structure
            ```
            project/
            ├── app.py
            ├── requirements.txt
            └── dataset/
                ├── your_simulation.e
                ├── your_simulation.e.part1
                └── your_simulation.e.part2
            ```
            ### MOOSE Input Example
            ```python
            [Outputs]
            exodus = true
            file_base = my_results
            []
            [Outputs/exodus]
            output_on = 'timestep_end'
            []
            ```
            ### Installation
            ```bash
            # Minimal
            pip install streamlit meshio plotly netCDF4
            # Full (with all exports)
            pip install streamlit meshio plotly netCDF4 h5py pandas
            ```
            """)
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: gray; padding: 1rem;">
    <small>
    MOOSE Exodus Viewer v3.0 |
    Built with Streamlit + Plotly + Meshio |
    <a href="https://mooseframework.inl.gov" target="_blank">MOOSE Framework</a>
    </small>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
