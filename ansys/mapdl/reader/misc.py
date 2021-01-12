"""Module for miscellaneous functions and methods"""
import tempfile
import os
import random
import string

from pyvista.utilities.errors import GPUInfo
import scooby
import pyvista
import numpy as np
import vtk

VTK9 = vtk.vtkVersion().GetVTKMajorVersion() >= 9


def vtk_cell_info(grid):
    """Returns version consistent connectivity and cell offset arrays.

    Notes
    -----
    VTKv9 changed the connectivity and offset arrays:

    Topology:
    ---------
    Cell 0: Triangle | point ids: {0, 1, 2}
    Cell 1: Triangle | point ids: {5, 7, 2}
    Cell 2: Quad     | point ids: {3, 4, 6, 7}
    Cell 4: Line     | point ids: {5, 8}

    VTKv9
    =====
    Offsets:      {0, 3, 6, 10, 12}
    Connectivity: {0, 1, 2, 5, 7, 2, 3, 4, 6, 7, 5, 8}

    Prior to VTKv9
    ==============
    Offsets:      {0, 4, 8, 13, 16}
    Connectivity: {3, 0, 1, 2, 3, 5, 7, 2, 4, 3, 4, 6, 7, 2, 5, 8}

    """
    if VTK9:
        # for pyvista < 0.25.0
        if not hasattr(grid, 'cell_connectivity'):
            carr = grid.GetCells()
            cells = vtk.util.numpy_support.vtk_to_numpy(carr.GetConnectivityArray())
        else:
            cells = grid.cell_connectivity
        offset = grid.offset - 1
    else:
        cells, offset = grid.cells, grid.offset

    if cells.dtype != np.int64:
        cells = cells.astype(np.int64)

    if offset.dtype != np.int64:
        offset = offset.astype(np.int64)

    return cells, offset


class Report(scooby.Report):
    """A class for custom scooby.Report."""

    def __init__(self, additional=None, ncol=3, text_width=80, sort=False,
                 gpu=True):
        """Generate a :class:`scooby.Report` instance.

        Parameters
        ----------
        additional : list(ModuleType), list(str)
            List of packages or package names to add to output information.

        ncol : int, optional
            Number of package-columns in html table; only has effect if
            ``mode='HTML'`` or ``mode='html'``. Defaults to 3.

        text_width : int, optional
            The text width for non-HTML display modes

        sort : bool, optional
            Alphabetically sort the packages

        gpu : bool
            Gather information about the GPU. Defaults to ``True`` but if
            experiencing renderinng issues, pass ``False`` to safely generate
            a report.

        """
        # Mandatory packages.
        core = ['pyansys', 'pyvista', 'vtk', 'numpy', 'scipy',
                'appdirs', 'ansys.mapdl.core']

        # Optional packages.
        optional = ['matplotlib', 'ansys.mapdl.corba']

        # Information about the GPU - bare except in case there is a rendering
        # bug that the user is trying to report.
        if gpu:
            try:
                extra_meta = [(t[1], t[0]) for t in GPUInfo().get_info()]
            except:
                extra_meta = ("GPU Details", "error")
        else:
            extra_meta = ("GPU Details", "None")

        scooby.Report.__init__(self, additional=additional, core=core,
                               optional=optional, ncol=ncol,
                               text_width=text_width, sort=sort,
                               extra_meta=extra_meta)

    def __repr__(self):
        add_text = '-'*79 + '\nPyMAPDL-Reader Software and Environment Report'
        return add_text + super().__repr__()


def is_float(input_string):
    """Returns true when a string can be converted to a float"""
    try:
        float(input_string)
        return True
    except ValueError:
        return False


def random_string(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def _configure_pyvista():
    """Configure PyVista's ``rcParams`` for pyansys"""
    import pyvista as pv
    pv.rcParams['interactive'] = True
    pv.rcParams["cmap"] = "jet"
    pv.rcParams["font"]["family"] = "courier"
    pv.rcParams["title"] = "pyansys"
    return


def break_apart_surface(surf, force_linear=True):
    """Break apart the faces of a vtk PolyData such that the points
    for each face are unique and each point is used only by one face.
    This leads to duplicate points, but allows multiple scalars per
    face.

    Parameters
    ----------
    surf : pyvista.PolyData
        Surface to break apart.

    force_linear : bool, optional
        When ``True``, converts quadratic faces to their linear counterparts.

    Returns
    -------
    bsurf : pyvista.PolyData
        Surface with unique points for each face.  Contains the
        original indices in point_arrays "orig_ind".

    """
    faces = surf.faces
    if faces.dtype != np.int64:
        faces = faces.astype(np.int64)

    from ansys.mapdl.reader import _binary_reader
    b_points, b_faces, idx = _binary_reader.break_apart_surface(surf.points,
                                                                faces,
                                                                surf.n_faces,
                                                                force_linear)
    bsurf = pyvista.PolyData(b_points, b_faces)
    bsurf.point_arrays['orig_ind'] = idx
    return bsurf


def chunks(l, n):
    """ Yield successive n-sized chunks from l """
    for i in range(0, len(l), n):
        yield l[i:i + n]


def unique_rows(a):
    """ Returns unique rows of a and indices of those rows """
    if not a.flags.c_contiguous:
        a = np.ascontiguousarray(a)

    b = a.view(np.dtype((np.void, a.dtype.itemsize * a.shape[1])))
    _, idx, idx2 = np.unique(b, True, True)

    return a[idx], idx, idx2


def create_temp_dir(tmpdir=None):
    """Create a new unique directory at a given temporary directory"""
    if tmpdir is None:
        tmpdir = tempfile.gettempdir()
    elif not os.path.isdir(tmpdir):
        os.makedirs(tmpdir)

    # in the *rare* case of a duplicate path
    path = os.path.join(tmpdir, random_string(10))
    while os.path.isdir(path):
        path = os.path.join(tempfile.gettempdir(), random_string(10))

    try:
        os.mkdir(path)
    except:
        raise RuntimeError('Unable to create temporary working '
                           'directory %s\n' % path +
                           'Please specify run_location=')

    return path


def no_return(fn):
    """Decorator to return nothing from the wrapped function"""
    def wrapper(*args, **kwargs):
        fn(*args, **kwargs)
    return wrapper
