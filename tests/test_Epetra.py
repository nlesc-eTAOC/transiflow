import pytest
import numpy
import os

from transiflow import Continuation
from transiflow import utils

from transiflow.interface import SciPy as SciPyInterface


def read_matrix(fname, m):
    from PyTrilinos import Epetra

    A = Epetra.CrsMatrix(Epetra.Copy, m, 27)

    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, fname), 'r') as f:
        for i in f.readlines():
            r, c, v = [j.strip() for j in i.strip().split(' ') if j]
            r = int(r) - 1
            c = int(c) - 1
            v = float(v)
            if A.MyGlobalRow(r):
                A[r, c] = v
        A.FillComplete()

    return A


def read_vector(fname, m):
    from transiflow.interface import Epetra as EpetraInterface

    vec = EpetraInterface.Vector(m)

    dirname = os.path.dirname(__file__)
    with open(os.path.join(dirname, fname), 'r') as f:
        for i, v in enumerate(f.readlines()):
            lid = m.LID(i)
            if lid != -1:
                vec[lid] = float(v.strip())
    return vec


def extract_sorted_row(A, i):
    values, indices = A.ExtractGlobalRowCopy(i)
    idx = sorted(range(len(indices)), key=lambda i: indices[i])
    return [indices[i] for i in idx], [values[i] for i in idx]


def extract_sorted_local_row(A, i):
    indices = A.jcoA[A.begA[i]:A.begA[i + 1]]
    values = A.coA[A.begA[i]:A.begA[i + 1]]
    idx = sorted(range(len(indices)), key=lambda i: indices[i])
    return [indices[i] for i in idx], [values[i] for i in idx]


def test_ldc():
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    nx = 4
    ny = nx
    nz = nx
    dim = 3
    dof = 4
    parameters = {'Reynolds Number': 100}
    n = nx * ny * nz * dof

    state = numpy.zeros(n)
    for i in range(n):
        state[i] = i + 1

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    state = interface.vector_from_array(state)

    A = interface.jacobian(state)
    rhs = interface.rhs(state)

    B = read_matrix('ldc_%sx%sx%s.txt' % (nx, ny, nz), interface.solve_map)
    rhs_B = read_vector('ldc_rhs_%sx%sx%s.txt' % (nx, ny, nz), interface.map)

    for i in range(n):
        lid = interface.solve_map.LID(i)
        if lid == -1:
            continue

        print(i, lid)

        indices_A, values_A = extract_sorted_row(A, i)
        indices_B, values_B = extract_sorted_row(B, i)

        print('Expected:')
        print(indices_B)
        print(values_B)

        print('Got:')
        print(indices_A)
        print(values_A)

        assert len(indices_A) == len(indices_B)
        for j in range(len(indices_A)):
            assert indices_A[j] == indices_B[j]
            assert values_A[j] == pytest.approx(values_B[j])

    for i in range(n):
        lid = interface.map.LID(i)
        if lid == -1:
            continue

        print(i, lid, rhs[lid], rhs_B[lid])

        assert rhs_B[lid] == pytest.approx(rhs[lid])


def test_ldc_stretched_file():
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    nx = 4
    ny = nx
    nz = nx
    dim = 3
    dof = 4
    parameters = {'Reynolds Number': 100, 'Grid Stretching': True}
    n = nx * ny * nz * dof

    state = numpy.zeros(n)
    for i in range(n):
        state[i] = i + 1

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    state = interface.vector_from_array(state)

    A = interface.jacobian(state)
    rhs = interface.rhs(state)

    B = read_matrix('ldc_stretched_%sx%sx%s.txt' % (nx, ny, nz), interface.solve_map)
    rhs_B = read_vector('ldc_stretched_rhs_%sx%sx%s.txt' % (nx, ny, nz), interface.map)

    for i in range(n):
        lid = interface.solve_map.LID(i)
        if lid == -1:
            continue

        print(i, lid)

        indices_A, values_A = extract_sorted_row(A, i)
        indices_B, values_B = extract_sorted_row(B, i)

        print('Expected:')
        print(indices_B)
        print(values_B)

        print('Got:')
        print(indices_A)
        print(values_A)

        assert len(indices_A) == len(indices_B)
        for j in range(len(indices_A)):
            assert indices_A[j] == indices_B[j]
            assert values_A[j] == pytest.approx(values_B[j])

    for i in range(n):
        lid = interface.map.LID(i)
        if lid == -1:
            continue

        print(i, lid, rhs[lid], rhs_B[lid])

        assert rhs_B[lid] == pytest.approx(rhs[lid])


def test_ldc_stretched(nx=4):
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    ny = nx
    nz = nx
    dim = 3
    dof = 4
    parameters = {'Reynolds Number': 100, 'Grid Stretching': True}
    n = nx * ny * nz * dof

    state = numpy.zeros(n)
    for i in range(n):
        state[i] = i + 1

    interface = SciPyInterface.Interface(parameters, nx, ny, nz, dim, dof)
    B = interface.jacobian(state)
    rhs_B = interface.rhs(state)

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    state = interface.vector_from_array(state)

    A = interface.jacobian(state)
    rhs = interface.rhs(state)

    for i in range(n):
        lid = interface.solve_map.LID(i)
        if lid == -1:
            continue

        print(i, lid)

        indices_A, values_A = extract_sorted_row(A, i)
        indices_B, values_B = extract_sorted_local_row(B, i)

        print('Expected:')
        print(indices_B)
        print(values_B)

        print('Got:')
        print(indices_A)
        print(values_A)

        assert len(indices_A) == len(indices_B)
        for j in range(len(indices_A)):
            assert indices_A[j] == indices_B[j]
            assert values_A[j] == pytest.approx(values_B[j])

    for i in range(n):
        lid = interface.map.LID(i)
        if lid == -1:
            continue

        print(i, lid, rhs[lid], rhs_B[lid])

        assert rhs_B[i] == pytest.approx(rhs[lid])


def test_ldc8_stretched():
    test_ldc_stretched(8)


def test_norm():
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    nx = 4
    ny = nx
    nz = nx
    dim = 3
    dof = 4
    parameters = {}
    n = nx * ny * nz * dof

    state = numpy.zeros(n)
    for i in range(n):
        state[i] = i + 1

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)

    state_dist = EpetraInterface.Vector.from_array(interface.map, state)
    assert utils.norm(state) == utils.norm(state_dist)

    state_dist = EpetraInterface.Vector.from_array(interface.solve_map, state)
    assert utils.norm(state) == utils.norm(state_dist)


def test_Epetra(nx=4):
    try:
        from transiflow.interface import Epetra as EpetraInterface
        from PyTrilinos import Teuchos
    except ImportError:
        pytest.skip("Epetra not found")

    numpy.random.seed(1234)

    dim = 3
    dof = 4
    ny = nx
    nz = nx

    parameters = Teuchos.ParameterList()
    parameters.set('Reynolds Number', 0)

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    continuation = Continuation(interface, parameters)

    x0 = interface.vector()
    x0.PutScalar(0.0)
    x0 = continuation.newton(x0)

    start = 0
    target = 100
    ds = 100
    x = continuation.continuation(x0, 'Reynolds Number', start, target, ds)[0]

    assert utils.norm(x) > 0


def _test_Epetra_2D(nx=8):
    try:
        from transiflow.interface import Epetra as EpetraInterface
        from PyTrilinos import Teuchos
    except ImportError:
        pytest.skip("Epetra not found")

    numpy.random.seed(1234)

    dim = 3
    dof = 4
    ny = nx
    nz = 1

    parameters = Teuchos.ParameterList()
    parameters.set('Reynolds Number', 0)
    parameters.set('Bordered Solver', True)

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    continuation = Continuation(interface, parameters)

    x0 = interface.vector()
    x0 = continuation.newton(x0)

    start = 0
    target = 2000
    ds = 100
    x = continuation.continuation(x0, 'Reynolds Number', start, target, ds)[0]

    assert utils.norm(x) > 0


def _test_Epetra_2D_stretched(nx=8):
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    numpy.random.seed(1234)

    dim = 3
    dof = 4
    ny = nx
    nz = 1

    parameters = {
        'Reynolds Number': 0,
        'Bordered Solver': True,
        'Grid Stretching': True,
        'Verbose': True
    }

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    continuation = Continuation(interface, parameters)

    x0 = interface.vector()
    x0 = continuation.newton(x0)

    start = 0
    target = 2000
    ds = 100
    x = continuation.continuation(x0, 'Reynolds Number', start, target, ds)[0]

    assert utils.norm(x) > 0


def _test_Epetra_rayleigh_benard(nx=8):
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    try:
        from transiflow import JadaInterface  # noqa: F401
    except ImportError:
        pytest.skip('jadapy not found')

    numpy.random.seed(1234)

    dim = 2
    dof = 4
    ny = nx
    nz = 1

    parameters = {
        'Problem Type': 'Rayleigh-Benard',
        'Prandtl Number': 10,
        'Biot Number': 1,
        'X-max': 10,
        'Bordered Solver': True
    }

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    continuation = Continuation(interface, parameters)

    x0 = interface.vector()
    x0 = continuation.newton(x0)

    start = 0
    target = 1700
    ds = 200
    x, mu = continuation.continuation(x0, 'Rayleigh Number', start, target, ds)

    parameters['Detect Bifurcation Points'] = True
    parameters['Eigenvalue Solver'] = {}
    parameters['Eigenvalue Solver']['Arithmetic'] = 'real'
    parameters['Eigenvalue Solver']['Number of Eigenvalues'] = 2

    target = 5000
    ds = 50
    x, mu = continuation.continuation(x, 'Rayleigh Number', mu, target, ds)

    assert utils.norm(x) > 0
    assert mu > 0
    assert mu < target


def _test_Epetra_double_gyre(nx=8):
    try:
        from transiflow.interface import Epetra as EpetraInterface
    except ImportError:
        pytest.skip("Epetra not found")

    try:
        from transiflow import JadaInterface  # noqa: F401
    except ImportError:
        pytest.skip('jadapy not found')

    numpy.random.seed(1234)

    dim = 2
    dof = 3
    ny = nx
    nz = 1

    parameters = {
        'Problem Type': 'Double Gyre',
        'Reynolds Number': 16,
        'Rossby Parameter': 1000,
        'Wind Stress Parameter': 0
    }

    parameters['Preconditioner'] = {}
    parameters['Preconditioner']['Number of Levels'] = 0

    interface = EpetraInterface.Interface(parameters, nx, ny, nz, dim, dof)
    continuation = Continuation(interface, parameters)

    x0 = interface.vector()

    start = 0
    target = 1000
    ds = 200
    x, mu = continuation.continuation(x0, 'Wind Stress Parameter', start, target, ds)

    parameters['Detect Bifurcation Points'] = True
    parameters['Destination Tolerance'] = 1e-4
    parameters['Eigenvalue Solver'] = {}
    parameters['Eigenvalue Solver']['Number of Eigenvalues'] = 2

    target = 100
    ds = 5
    x, mu = continuation.continuation(x, 'Reynolds Number', 16, target, ds)

    assert utils.norm(x) > 0
    assert mu > 16
    assert mu < target
