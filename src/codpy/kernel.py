import numpy as np
from codpydll import *
from sklearn import linear_model
from sklearn.preprocessing import PolynomialFeatures

import codpy.core as core
from codpy.algs import alg
from codpy.core import diffops
from codpy.lalg import lalg as lalg
from codpy.permutation import lsap


class Kernel:
    """
    A kernel class
    """
    def __init__(
        self,
        max_pool: int = 1000,
        max_nystrom: int = 1000,
        reg: float = 1e-9,
        order: int = None,
        dim: int = 1,
        set_kernel: callable = None,
        **kwargs: dict,
    ) -> None:
        """
        Initializes the Kernel class with default or user-defined parameters and sets up the kernel function.

        :param max_pool: Maximum pool size for the kernel operations. Defaults to 1000.
        :type max_pool: :class:`int`, optional
        :param max_nystrom: Maximum number of Nystrom samples. Defaults to 1000.
        :type max_nystrom: :class:`int`, optional
        :param reg: Regularization parameter for kernel operations. Defaults to 1e-9.
        :type reg: :class:`float`, optional
        :param order: Polynomial order for polynomial kernel functions. Defaults to ``None``.
        :type order: :class:`int`, optional
        :param dim: Dimensionality of the input data. Defaults to 1.
        :type dim: :class:`int`, optional
        :param set_kernel: A custom kernel function initializer. If not provided, a default kernel is used.
        :type set_kernel: :class:`callable`, optional
        :param kwargs: Additional keyword arguments for further customization.
        :type kwargs: :class:`dict`
        """
        self.dim = dim
        self.order = order
        self.reg = reg
        self.max_pool = int(max_pool)
        self.max_nystrom = int(max_nystrom)

        if set_kernel is not None:
            self.set_kernel = set_kernel
        else:
            self.set_kernel = self.default_kernel_functor()
        self.x = None
        if kwargs.get("x", None) is not None or kwargs.get("fx", None) is not None:
            self.set(**kwargs)

    def default_kernel_functor(self):
        """
        Provides the default kernel initializer.

        Returns:
            :class:`callable`: The default kernel initialization function using :func:`core.kernel_setter`.
        """
        return core.kernel_setter("maternnorm", "standardmean", 0, 1e-9)

    def set_custom_kernel(
        self,
        kernel_name: str,
        map_name: str,
        poly_order: int = 0,
        reg: float = None,
        bandwidth: float = 1.0,
    ) -> None:
        """
        Set a custom kernel using `core.kernel_helper2` with flexible parameters.

        :param kernel_name: Name of the kernel function to use (e.g., ``'gaussian'``).
        :type kernel_name: :class:`str`
        :param map_name: Name of the mapping function (e.g., ``'standardmean'``).
        :type map_name: :class:`str`
        :param poly_order: The polynomial order if using a polynomial kernel. Defaults to 0.
        :type poly_order: :class:`int`, optional
        :param reg: Regularization parameter. If not provided, uses the instance's `reg` value.
        :type reg: :class:`float`, optional
        :param bandwidth: Bandwidth for kernel functions that require it. Defaults to 1.0.
        :type bandwidth: :class:`float`, optional

        :returns: None
        """
        reg = reg if reg is not None else self.reg
        kernel_function = core.kernel_setter(
            kernel_name, map_name, poly_order, reg, bandwidth
        )
        ## tester!!!!!!!!!!!!!!!!!!!
        self = Kernel(set_kernel=kernel_function)

    def get_order(self) -> int:
        """
        Retrieve the polynomial order for the kernel.

        :returns: The polynomial order if available, otherwise ``None``.
        :rtype: :class:`int` or :class:`None`

        Example:
            >>> order = kernel.get_order()
        """
        if not hasattr(self, "order"):
            self.order = None
        return self.order

    def _set_polynomial_regressor(self, x=None, fx=None):
        if x is None or fx is None or self.get_order() is None:
            self.polyvariables, self.polynomial_kernel, self.polynomial_values = (
                None,
                None,
                None,
            )
            return
        order = self.get_order()
        if order is not None and fx is not None and x is not None:
            self.polyvariables = PolynomialFeatures(order).fit_transform(x)
            self.polynomial_kernel = linear_model.LinearRegression().fit(
                self.polyvariables, fx
            )
            self.polynomial_values = self.polynomial_kernel.predict(self.polyvariables)
            self.set_theta(None)

    def get_polynomial_values(self):
        if self.get_order() is None:
            return None
        if not hasattr(self, "polynomial_values") or self.polynomial_values is None:
            self._set_polynomial_regressor(self.get_x(), self.get_fx())
        return self.polynomial_values

    def _get_polyvariables(self):
        if self.get_order() is None:
            return None
        if not hasattr(self, "polyvariables") or self.polyvariables is None:
            self._set_polynomial_regressor(self.get_x(), self.get_fx())
        return self.polyvariables

    def _get_polynomial_kernel(self, **kwargs):
        if self.get_order() is None:
            return None
        if not hasattr(self, "polynomial_kernel") or self.polynomial_kernel is None:
            self._set_polynomial_regressor(self.get_x(), self.get_fx())
        return self.polynomial_kernel

    def get_polynomial_regressor(
        self, z: np.ndarray, x: np.ndarray = None, fx: np.ndarray = None
    ) -> np.ndarray:
        """
        Set up the polynomial regressor based on the input data and the polynomial order.

        :param z: New input data points for the regressor.
        :type z: :class:`numpy.ndarray`
        :param x: Input data points.
        :type x: :class:`numpy.ndarray`, optional
        :param fx: Function values corresponding to the input data.
        :type fx: :class:`numpy.ndarray`, optional

        :returns: The predicted polynomial values or `None` if unavailable.
        :rtype: :class:`numpy.ndarray` or :class:`None`

        Example:
            >>> z_data = np.random.rand(100, 10)
            >>> pred = kernel.get_polynomial_regressor(z_data)
        """
        if self.get_order() is None:
            return None
        if x is None:
            polyvariables = self._get_polyvariables()
        else:
            polyvariables = PolynomialFeatures(self.order).fit_transform(x)
        if fx is None:
            polynomial_kernel = self._get_polynomial_kernel()
        else:
            polynomial_kernel = linear_model.LinearRegression().fit(polyvariables, fx)
        z_polyvariables = PolynomialFeatures(self.order).fit_transform(z)
        if polynomial_kernel is not None:
            return polynomial_kernel.predict(z_polyvariables)
        return None

    def Knm(self, x: np.ndarray, y: np.ndarray, fy: np.ndarray = []) -> np.ndarray:
        """
        Compute the kernel matrix :math:`K(x, y)` using the current kernel settings.

        :param x: Input data points (N, D), where N is the number of points and D is the dimensionality.
        :type x: :class:`numpy.ndarray`
        :param y: Secondary data points (M, D), where M is the number of points and D is the dimensionality.
        :type y: :class:`numpy.ndarray`
        :param fy: Optional function values for kernel computation.
        :type fy: :class:`numpy.ndarray`, optional

        :returns: The computed kernel matrix (N, M).
        :rtype: :class:`numpy.ndarray`

        Example:
            >>> x_data = np.array([...])
            >>> y_data = np.array([...])
            >>> kernel_matrix = Kernel(x=x_data,y=y_data).Knm()
        """

        self.set_kernel_ptr()
        return core.op.Knm(x=x, y=y, fy=fy)

    def get_knm_inv(
        self, epsilon: float = None, epsilon_delta: np.ndarray = None, **kwargs
    ) -> np.ndarray:
        """
        Retrieve the inverse of the kernel matrix :math:`K^{-1}(x, y)` using least squares computations.

        :param epsilon: Regularization parameter for the inverse computation. Defaults to None.
        :type epsilon: :class:`float`, optional
        :param epsilon_delta: Delta values for adjusting regularization. Defaults to None.
        :type epsilon_delta: :class:`numpy.ndarray`, optional

        :returns: The inverse kernel matrix or the product with function values if provided.
        :rtype: :class:`numpy.ndarray`

        Notes:
            - If the regularization parameter (`reg`) is empty:
                - If `fx` is empty: Returns a NumPy array of size (N, M), representing the least square inverse of :math:`K_{nm}(x, y)`.
                - If `fx` is provided: Returns the product of :math:`K^{-1}_{nm}(x, y)` and `fx`. This allows performance and memory optimizations.
            - If the regularization parameter (`reg`) is provided:
                - If `fx` is empty: Returns a NumPy array of size (N, M), computed as:
                    :math:`(K_{nm}(y, x) K_{nm}(x, y) + \text{reg})^{-1} K_{nm}(y, x)`.
                - If `fx` is provided: Returns the product of :math:`K^{-1}_{nm}(x, y)` and `fx`.

        Example:

            >>> x_data = np.random.rand(100, 10)
            >>> y_data = np.random.rand(80, 10)
            >>> fx_data = np.random.rand(80, 5)
            >>> inv_kernel = kernel.get_knm_inv(x=x_data, y=y_data, fx=fx_data)
        """
        if not hasattr(self, "knm_inv"):
            self.knm_inv = None
        if self.knm_inv is None:
            epsilon = kwargs.get("epsilon", self.reg)
            epsilon_delta = kwargs.get("epsilon_delta", None)
            if epsilon_delta is None:
                epsilon_delta = []
            else:
                epsilon_delta = epsilon_delta * self.get_Delta()
            self._set_knm_inv(
                core.op.Knm_inv(
                    x=self.get_x(),
                    y=self.get_y(),
                    epsilon=epsilon,
                    reg_matrix=epsilon_delta,
                ),
                **kwargs,
            )
        return self.knm_inv

    def get_knm(self) -> np.ndarray:
        """
        Retrieve or compute the Gram matrix :math:`K(x, y)` for the kernel.

        :returns: The Gram matrix.
        :rtype: :class:`numpy.ndarray`
        """
        if not hasattr(self, "knm") or self.knm is None:
            self._set_knm(core.op.Knm(x=self.x, y=self.y))
        return self.knm

    def _set_knm_inv(self, k):
        self.knm_inv = k
        self.set_theta(None)

    def _set_knm(self, k):
        self.knm = k

    def get_x(self) -> np.ndarray:
        """
        Retrieve the input data `x`.

        :returns: The input data or `None` if not set.
        :rtype: :class:`numpy.ndarray` or :class:`None`
        """
        if not hasattr(self, "x"):
            self.x = None
        return self.x

    def set_x(self, x: np.ndarray, set_polynomial_regressor: bool = True) -> None:
        """
        Set the input data `x` for the kernel.

        :param x: Input data points.
        :type x: :class:`numpy.ndarray`
        :param set_polynomial_regressor: Whether to set the polynomial regressor after setting the data. Defaults to True.
        :type set_polynomial_regressor: :class:`bool`, optional
        """
        self.x = x.copy()
        self.set_y()
        if set_polynomial_regressor:
            self._set_polynomial_regressor()
        self._set_knm_inv(None)
        self._set_knm(None)
        self.rescale()

    def set_y(self, y=None):
        """
        If Y is provided then interpolation/extrapolation the following formula is used
        f_{\theta}(.) = K(.,Y)theta, theta = K(X,Y)^{-1}f(X)
        By default: Y = X

        Notes:
            Formule interpolation/extrapolation f_{\theta}(.) = K(.,Y)theta, theta = K(X,Y)^{-1}f(X)
            By default: Y = X
        """
        if y is None:
            self.y = self.get_x()
        else:
            self.y = y.copy()

    def get_y(self):
        if not hasattr(self, "y") or self.y is None:
            self.set_y()
        return self.y

    def get_fx(self):
        if not hasattr(self, "fx"):
            self.fx = None
        return self.fx

    def set_fx(self, fx, set_polynomial_regressor=True):
        if fx is not None:
            self.fx = fx.copy()
        else:
            self.fx = None
        if set_polynomial_regressor:
            self._set_polynomial_regressor()
        self.set_theta(None)

    def set_theta(self, theta):
        """
        theta coefficient assignment in
        theta = K(X,Y)^{-1}f(x)
        """
        self.theta = theta
        if theta is None:
            return
        self.fx = None
        # self.fx =  lalg.prod(self.get_knm(),self.theta)
        # if self.get_order() is not None :
        #     self.fx += self.get_polynomial_regressor(z=self.get_x())

    def get_theta(self):
        if not hasattr(self, "theta") or self.theta is None:
            if self.get_order() is not None and self.get_fx() is not None:
                fx = self.fx - self.get_polynomial_regressor(z=self.get_x())
            else:
                ##
                fx = self.get_fx()
            if fx is None:
                self.theta = None
            else:
                ##
                self.theta = lalg.prod(self.get_knm_inv(), fx)
        return self.theta

    def get_Delta(self):
        """
        Get discrete Laplace-Beltrami operator
        """
        if self.Delta is None:
            self.Delta = diffops.nablaT_nabla(self.y, self.x)
        return self.Delta

    def select(self, x, N, fx=None, all=False, norm_="frobenius", **kwargs):
        """
        norm_ : `"frobenius"`, `"classifier"`
        `"classifier"` is a norm adapted to fx representing probabilities to be in a given label class: ||f - f_{k,\theta}(.)||
        ||A - B|| = ||A/A.sum(axis=-1) - B.sum(axis=-1)||_{\ell^2} : .. A \in N,D, B \in N,D
        """
        # check if the number of y's is passed
        if N is None:
            N = self.max_nystrom

        self.set_x(x)
        self.set_fx(fx)
        self.rescale()
        # if fx was passed, apply polynomial regression to x
        if self.get_fx() is not None:
            if self.get_polynomial_values() is not None:
                polynomial_values = self.get_polynomial_regressor(z=self.get_x())
                # Polynomial error in the function's approximation
                fx = self.fx - polynomial_values
            else:
                fx = self.fx
            # Apply hybrid greedy Nystrom with error between ||f .-f_{k,\theta}||_A and  wrt a given norm
            # udefined by user
            # to compute Y
            theta, indices = alg.HybridGreedyNystroem(
                x=self.get_x(), fx=fx, N=N, tol=0.0, error_type=norm_, **kwargs
            )
            #
            if all is False:
                # if there is a flag all, then
                # f_\theta(.) = K(.,Y)K(X,Y)^{-1}f(X)
                self.set(
                    x=self.x,
                    y=self.x[indices],
                    fx=self.fx,
                    set_polynomial_regressor=False,
                )
            else:
                # else X = Y is set:
                #  f_\theta(.) = K(.,Y)K(Y,Y)^{-1}f(Y)
                self.set_x(self.x[indices], set_polynomial_regressor=False)
                self.set_fx(self.fx[indices], set_polynomial_regressor=False)
                self.set_theta(theta)
            return indices

        # if the size of x <= N, then it returns corresponding indices

        if self.x.shape[0] <= N:
            indices = list(range(self.x.shape[0]))
            return indices

        # if the size of x => N, then it
        # returns the points having the largest distance
        # with respect to maximum mean discrepancy (MMD)
        indices = [0]
        complement_indices = list(range(1, N))
        for n in range(N - 1):
            # Computed MMD distance matrix
            Dnm = core.op.Dnm(x[indices], x[complement_indices])
            indice = np.max(Dnm, axis=0)
            # selects the indices with maximum MMD
            indice = np.argmax(indice)
            indice = complement_indices[indice]
            complement_indices.remove(indice)
            indices.append(indice)
            pass

        # updates x
        self.set_x(self.x[indices])
        return indices

    def set(self, x=None, fx=None, y=None):
        if x is None and fx is None:
            return
        if x is not None and fx is None:
            self.set_x(core.get_matrix(x.copy()))
            self.set_y(y=y)
            self.set_fx(None)
            self.rescale()

        if x is None and fx is not None:
            if self.kernel is None:
                raise Exception("Please input x at least once")
            if fx.shape[0] != self.x.shape[0]:
                raise Exception(
                    "fx of size "
                    + str(fx.shape[0])
                    + "must have the same size as x"
                    + str(self.x.shape[0])
                )
            self.set_fx(core.get_matrix(fx))

        if x is not None and fx is not None:
            self.set_x(x), self.set_fx(fx),self.set_y(y=y)
            self.rescale()
            pass
        return self

    def map(
        self, x: np.ndarray, y: np.ndarray, distance: str = None, sub: bool = False
    ) -> None:
        r"""
        Maps the input data points `x` to the target data points `y` using the kernel and optimal transport techniques.

        :param x: Input data points (N, D_source).
        :type x: :class:`numpy.ndarray`
        :param y: Target data points (M, D_target).
        :type y: :class:`numpy.ndarray`
        :param distance: Distance metric to use in mapping. Defaults to None.
        :type distance: :class:`str`, optional
        :param sub: Whether to apply a sub-permutation. Defaults to False.
        :type sub: :class:`bool`, optional

        :returns: None

        Notes:

           This method computes a permutation that maps `x` to `y` using the Linear Sum Assignment Problem (LSAP).
           If the dimensionality of :math:`x` and :math:`y` is the same, the classical LSAP is applied to find the optimal mapping.
           If the dimensionalities differ (i.e., :math:`D_{source} \neq D_{target}`), the method encodes the data into
           a lower-dimensional latent space and then applies a descent-based method to solve for the permutation,
           acting as a form of discrete optimal transport.

            - If the dimensionalities of `x` and `y` are the same (:math:`D_{source} = D_{target}`), the classical LSAP algorithm is used.
            - If the dimensionalities differ (:math:`D_{source} \neq D_{target}`), a descent-based method is used to encode the data into a lower-dimensional latent space
            before finding the optimal permutation, following principles of discrete optimal transport.
            - This permutation can be used to transform the input data `x` to approximate the target data `y`.


        Example:

            >>> x_data = np.array([...])  # Input data with shape (N, D_source)
            >>> y_data = np.array([...])  # Target data with shape (M, D_target)
            >>> kernel.map(x_data, y_data)
        """
        self.set_x(x), self.set_fx(y)
        self.rescale()

        if x.shape[1] != y.shape[1]:
            self.permutation = cd.alg.encoder(self.get_x(), self.get_fx())
        else:
            D = core.op.Dnm(x=x, y=y, distance=distance)
            self.permutation = lsap(D, bool(sub))
        # self.set_fx(self.get_fx()[self.permutation])
        self.set_x(self.get_x()[self.permutation])
        return self

    def __len__(self):
        """ """
        if self.x is None:
            return 0
        return self.x.shape[0]

    def update_set(self, z, fz, **kwargs):
        """ """
        return z[-self.max_pool :], fz[-self.max_pool :]

    def update(self, z, fz, eps=None, **kwargs):
        """
        This method allows to define a regressor
        defined on the set X, but fit to others value z,fz
        :math: f_{k, theta}(Z) ~  K(Z,X)theta = f(Z)
        :math: theta = K(Z,X)^{-1}f(Z)
        """
        self.set_kernel_ptr()
        if isinstance(z, list):
            return [self.__call__(x, **kwargs) for x in z]
        z = core.get_matrix(z)
        if self.x is None:
            return None
        Knm = core.op.Knm(x=z, y=self.get_y())
        if self.order is not None:
            fzz = fz - self.get_polynomial_regressor(z)
        else:
            fzz = fz
        # err = self(z)-fz
        # err= (err**2).sum()
        if eps is None:
            eps = self.reg
        # if self.theta is not None: fzz += eps*lalg.prod(Knm,self.theta)
        # computes theta
        self.set_theta(lalg.lstsq(Knm, fzz, eps=eps))
        # err = self(z)-fz
        # err= (err**2).sum()

        if self.order is not None:
            self.fx += self.get_polynomial_regressor(z=self.get_x())

        return self

    def add(self, y=None, fy=None):
        """
        The method allows optimized computation
        for training set augmentation.

        :math:K([X,Y], [X,Y]) \in (N_X+N_Y), (N_X+N_Y)
        :math:(N_X+N_Y)^3, while using the block-inversion
        algorithm allows to reduce to :math: N_X^3 + N_Y^3.
        :math:f_{k,theta}(.) = K(., [X,Y])theta, theta = K([X,Y], [X,Y])^{-1}[[f(X); f(Y)]]
        where [.] denotes standard matrix concatenation.

        """
        x, fx = core.get_matrix(y.copy()), core.get_matrix(fy.copy())
        # if self.x is not None and x is not None: x=np.concatenate([self.x,x.copy()])[-self.max_pool:]
        # if self.fx is not None and fx is not None: fx=np.concatenate([self.fx,fx.copy()])[-self.max_pool:]
        if not hasattr(self, "x") or self.x is None:
            self.set(x, fx)
            return

        # the method add computes an updated Gram matrix using the already
        # pre-computed Gram matrix K(x,x).
        self.Knm, self.Knm_inv, y = alg.add(
            self.get_knm(), self.get_knm_inv(), self.get_x(), x
        )
        self.set_x(y)
        if fx is not None and self.get_fx() is not None:
            self.set_fx(np.concatenate([fx, self.get_fx()], axis=0))
        else:
            self.set_fx(fx)

        self._set_polynomial_regressor()
        return self

    def kernel_distance(self, z):
        """
        return an MMD based distance matrix:
        :math:d(x,z) = K(x,x) + K(z,z)-2K(x,z)
        """
        return core.op.Dnm(x=z, y=self.x)

    def get_kernel(self):
        """
        PSD kernel function:
        k(S(x),S(y)) where S is a defined map.
        """
        if not hasattr(self, "kernel"):
            self.set_kernel()
            # self.order= None
            self.kernel = core.kernel_interface.get_kernel_ptr()
        return self.kernel

    def set_kernel_ptr(self):
        """
        Set codpy interface to the current kernel function
        """
        core.kernel_interface.set_kernel_ptr(self.get_kernel())
        core.kernel_interface.set_polynomial_order(0)
        core.kernel_interface.set_regularization(self.reg)

    def rescale(self) -> None:
        """
        Rescales the input data.
        """
        # instructs to set kernel
        self.set_kernel_ptr()
        if self.get_x() is not None:
            # instructs to set the map parameter
            # applied to the data
            core.kernel_interface.rescale(self.get_x(),max = self.max_nystrom)
            # retrives the kernel
            self.kernel = core.kernel_interface.get_kernel_ptr()

    def __call__(self, z: np.ndarray) -> np.ndarray:
        """
        Predict the output using the kernel for input data `z`.

        :param z: Input data points for prediction.
        :type z: :class:`numpy.ndarray`

        :returns: The predicted values based on the kernel and function values.
        :rtype: :class:`numpy.ndarray`

        Example:
            >>> z_data = np.array([...])
            >>> prediction = kernel(z_data)

        Note:
            The function is similar to obj.predict
            in scikit-learn, xgboost etc.
            If fx was defined, then it :math:f_{k, \theta}(z)
            if fx was not defined, then it returns
            the projection operator:
            :math:P_{k,\theta}(z) = K(Z,K)K(X,X)^{-1}
        """

        z = core.get_matrix(z)

        # Don't forget to set the kernel
        self.set_kernel_ptr()

        fy = self.get_theta()

        if fy is None:
            fy = self.get_knm_inv()

        Knm = core.op.Knm(x=z, y=self.get_y(), fy=fy)

        if self.order is not None:
            polynomial_regressor = self.get_polynomial_regressor(z)
            Knm += polynomial_regressor

        return Knm
