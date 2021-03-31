import numpy

from scipy import sparse
from scipy.sparse import linalg

from fvm import Discretization

class Interface:
    def __init__(self, parameters, nx, ny, nz, dim, dof, x=None, y=None, z=None):
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.dim = dim
        self.dof = dof
        self.discretization = Discretization(parameters, nx, ny, nz, dim, dof, x, y, z)

    def set_parameter(self, name, value):
        self.discretization.set_parameter(name, value)

    def get_parameter(self, name):
        return self.discretization.get_parameter(name)

    def rhs(self, state):
        return self.discretization.rhs(state)

    def jacobian(self, state):
        return self.discretization.jacobian(state)

    def mass_matrix(self):
        return self.discretization.mass_matrix()

    def solve(self, jac, rhs):
        coA = numpy.zeros(jac.begA[-1], dtype=jac.coA.dtype)
        jcoA = numpy.zeros(jac.begA[-1], dtype=int)
        begA = numpy.zeros(len(jac.begA), dtype=int)

        idx = 0
        for i in range(len(jac.begA)-1):
            if i == self.dim:
                coA[idx] = -1.0
                jcoA[idx] = i
                idx += 1
                begA[i+1] = idx
                continue
            for j in range(jac.begA[i], jac.begA[i+1]):
                if jac.jcoA[j] != self.dim:
                    coA[idx] = jac.coA[j]
                    jcoA[idx] = jac.jcoA[j]
                    idx += 1
            begA[i+1] = idx

        A = sparse.csr_matrix((coA, jcoA, begA))
        if len(rhs.shape) < 2:
            rhs[self.dim] = 0
            x = linalg.spsolve(A, rhs)
        else:
            x = rhs.copy()
            rhs[self.dim, :] = 0
            for i in range(x.shape[1]):
                x[:, i] = linalg.spsolve(A, rhs[:, i])
        return x
