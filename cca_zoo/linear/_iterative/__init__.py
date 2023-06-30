from ._altmaxvar import AltMaxVar
from ._elasticnet import SCCA_IPLS, ElasticCCA
from ._pls_als import PLS_ALS
from ._scca_pmd import SCCA_PMD
from ._scca_parkhomenko import SCCA_Parkhomenko
from ._scca_span import SCCA_Span

__all__ = [
    "ElasticCCA",
    "SCCA_IPLS",
    "PLS_ALS",
    "SCCA_PMD",
    # "SCCA_ADMM",
    "SCCA_Parkhomenko",
    "SCCA_Span",
    # "SWCCA",
    # "GradKCCA",
    # "SCCA_HSIC",
    "AltMaxVar",
    # "PLSGHA",
]
