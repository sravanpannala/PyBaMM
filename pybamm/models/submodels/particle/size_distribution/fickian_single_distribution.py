#
# Class for a single particle-size distribution representing an
# electrode, with Fickian diffusion within each particle
#
import pybamm

from .base_distribution import BaseSizeDistribution


class FickianSingleSizeDistribution(BaseSizeDistribution):
    """Class for molar conservation in a single (i.e., x-averaged) particle-size
    distribution with Fickian diffusion within each particle.

    Parameters
    ----------
    param : parameter class
        The parameters to use for this submodel
    domain : str
        The domain of the model either 'Negative' or 'Positive'


    **Extends:** :class:`pybamm.particle.BaseSizeDistribution`
    """

    def __init__(self, param, domain):
        super().__init__(param, domain)
        pybamm.citations.register("Kirk2020")

    def get_fundamental_variables(self):
        if self.domain == "Negative":
            # distribution variables
            c_s_xav_distribution = pybamm.Variable(
                "X-averaged negative particle concentration distribution",
                domain="negative particle",
                auxiliary_domains={
                    "secondary": "negative particle size",
                    "tertiary": "current collector",
                },
                bounds=(0, 1),
            )
            # Since concentration does not depend on "x", need a particle-size
            # spatial variable R with only "current collector" as an auxiliary
            # domain
            R = pybamm.SpatialVariable(
                "R_n",
                domain=["negative particle size"],
                auxiliary_domains={"secondary": "current collector"},
                coord_sys="cartesian",
            )

        elif self.domain == "Positive":
            # distribution variables
            c_s_xav_distribution = pybamm.Variable(
                "X-averaged positive particle concentration distribution",
                domain="positive particle",
                auxiliary_domains={
                    "secondary": "positive particle size",
                    "tertiary": "current collector",
                },
                bounds=(0, 1),
            )
            # Since concentration does not depend on "x", need a particle-size
            # spatial variable R with only "current collector" as an auxiliary
            # domain
            R = pybamm.SpatialVariable(
                "R_p",
                domain=["positive particle size"],
                auxiliary_domains={"secondary": "current collector"},
                coord_sys="cartesian",
            )

        # Distribution variables
        variables = self._get_distribution_variables(R)

        # Concentration distribution variables (R-dependent)
        variables.update(
            self._get_standard_concentration_distribution_variables(
                c_s_xav_distribution
            )
        )

        # Standard R-averaged variables. Average concentrations using
        # the volume-weighted distribution since they are volume-based
        # quantities. Necessary for output variables "Total lithium in
        # negative electrode [mol]", etc, to be calculated correctly
        f_v_dist = variables[
            "X-averaged " + self.domain.lower()
            + " volume-weighted particle-size distribution"
        ]
        c_s_xav = pybamm.Integral(f_v_dist * c_s_xav_distribution, R)
        c_s = pybamm.SecondaryBroadcast(c_s_xav, [self.domain.lower() + " electrode"])
        variables.update(
            self._get_standard_concentration_variables(c_s, c_s_xav)
        )
        return variables

    def get_coupled_variables(self, variables):
        c_s_xav_distribution = variables[
            "X-averaged " + self.domain.lower() + " particle concentration distribution"
        ]
        R_spatial_variable = variables[self.domain + " particle sizes"]

        # broadcast to "particle size" domain then again into "particle"
        T_k_xav = pybamm.PrimaryBroadcast(
            variables["X-averaged " + self.domain.lower() + " electrode temperature"],
            [self.domain.lower() + " particle size"],
        )
        T_k_xav = pybamm.PrimaryBroadcast(T_k_xav, [self.domain.lower() + " particle"],)

        if self.domain == "Negative":
            N_s_xav_distribution = -self.param.D_n(
                c_s_xav_distribution, T_k_xav
            ) * pybamm.grad(c_s_xav_distribution)
        elif self.domain == "Positive":
            N_s_xav_distribution = -self.param.D_p(
                c_s_xav_distribution, T_k_xav
            ) * pybamm.grad(c_s_xav_distribution)

        # Standard R-averaged flux variables. Average using the area-weighted
        # distribution
        f_a_dist = variables[
            "X-averaged " + self.domain.lower()
            + " area-weighted particle-size distribution"
        ]
        f_a_dist = pybamm.PrimaryBroadcast(
            f_a_dist, [self.domain.lower() + " particle"],
        )
        # must use "R_spatial_variable" as integration variable, since "R" is a
        # broadcast
        N_s_xav = pybamm.Integral(f_a_dist * N_s_xav_distribution, R_spatial_variable)
        N_s = pybamm.SecondaryBroadcast(N_s_xav, [self.domain.lower() + " electrode"])
        variables.update(self._get_standard_flux_variables(N_s, N_s_xav))

        # Standard distribution flux variables (R-dependent)
        # (Cannot currently broadcast to "x" as cannot have 4 domains)
        variables.update(
            {
                "X-averaged "
                + self.domain.lower()
                + " particle flux distribution": N_s_xav_distribution,
            }
        )

        variables.update(self._get_total_concentration_variables(variables))
        return variables

    def set_rhs(self, variables):
        # Extract x-av variables
        c_s_xav_distribution = variables[
            "X-averaged " + self.domain.lower() + " particle concentration distribution"
        ]

        N_s_xav_distribution = variables[
            "X-averaged " + self.domain.lower() + " particle flux distribution"
        ]

        # Spatial variable R, broadcast into particle
        R_spatial_variable = variables[self.domain + " particle sizes"]
        R = pybamm.PrimaryBroadcast(
            R_spatial_variable, [self.domain.lower() + " particle"],
        )
        if self.domain == "Negative":
            self.rhs = {
                c_s_xav_distribution: -(1 / self.param.C_n)
                * pybamm.div(N_s_xav_distribution)
                / R ** 2
            }
        elif self.domain == "Positive":
            self.rhs = {
                c_s_xav_distribution: -(1 / self.param.C_p)
                * pybamm.div(N_s_xav_distribution)
                / R ** 2
            }

    def set_boundary_conditions(self, variables):
        # Extract x-av variables
        c_s_xav_distribution = variables[
            "X-averaged " + self.domain.lower() + " particle concentration distribution"
        ]
        c_s_surf_xav_distribution = variables[
            "X-averaged "
            + self.domain.lower()
            + " particle surface concentration distribution"
        ]
        j_xav_distribution = variables[
            "X-averaged "
            + self.domain.lower()
            + " electrode interfacial current density distribution"
        ]
        R = variables[self.domain + " particle sizes"]

        # Extract x-av T and broadcast to particle size domain
        T_k_xav = variables[
            "X-averaged " + self.domain.lower() + " electrode temperature"
        ]
        T_k_xav = pybamm.PrimaryBroadcast(
            T_k_xav, [self.domain.lower() + " particle size"]
        )

        # Set surface Neumann boundary values
        if self.domain == "Negative":
            rbc = (
                -self.param.C_n
                * R
                * j_xav_distribution
                / self.param.a_R_n
                / self.param.D_n(c_s_surf_xav_distribution, T_k_xav)
            )

        elif self.domain == "Positive":
            rbc = (
                -self.param.C_p
                * R
                * j_xav_distribution
                / self.param.a_R_p
                / self.param.gamma_p
                / self.param.D_p(c_s_surf_xav_distribution, T_k_xav)
            )

        self.boundary_conditions = {
            c_s_xav_distribution: {
                "left": (pybamm.Scalar(0), "Neumann"),
                "right": (rbc, "Neumann"),
            }
        }

    def set_initial_conditions(self, variables):
        """
        For single particle-size distribution models, initial conditions can't
        depend on x so we arbitrarily set the initial values of the single
        particles to be given by the values at x=0 in the negative electrode
        and x=1 in the positive electrode. Typically, supplied initial
        conditions are uniform x.
        """
        c_s_xav_distribution = variables[
            "X-averaged " + self.domain.lower() + " particle concentration distribution"
        ]

        if self.domain == "Negative":
            c_init = self.param.c_n_init(0)

        elif self.domain == "Positive":
            c_init = self.param.c_p_init(1)

        self.initial_conditions = {c_s_xav_distribution: c_init}

    def set_events(self, variables):
        c_s_surf_xav_distribution = variables[
            "X-averaged "
            + self.domain.lower()
            + " particle surface concentration distribution"
        ]
        tol = 1e-4

        self.events.append(
            pybamm.Event(
                "Minimum " + self.domain.lower() + " particle surface concentration",
                pybamm.min(c_s_surf_xav_distribution) - tol,
                pybamm.EventType.TERMINATION,
            )
        )

        self.events.append(
            pybamm.Event(
                "Maximum " + self.domain.lower() + " particle surface concentration",
                (1 - tol) - pybamm.max(c_s_surf_xav_distribution),
                pybamm.EventType.TERMINATION,
            )
        )
