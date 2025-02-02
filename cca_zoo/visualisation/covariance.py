import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


class CovarianceHeatmapDisplay:
    """Covariance Heatmap Display

    Heatmap of the covariances between the latent variables of the views.

    Parameters
    ----------
    train_covariances : np.ndarray
        The train covariances between views.
    test_covariances : np.ndarray
        The test covariances between views.

    Attributes
    ----------
    figure_ : matplotlib.pyplot.figure
        The figure of the plot.

    Examples
    --------
    >>> from cca_zoo.visualisation import CovarianceHeatmapDisplay
    >>> import matplotlib.pyplot as plt
    >>> import numpy as np
    >>> from cca_zoo.linear import MCCA
    >>>
    >>> # Generate Sample Data
    >>> # --------------------
    >>> X = np.random.rand(100, 10)
    >>> Y = np.random.rand(100, 10)
    >>>
    >>> # Splitting the data into training and testing sets
    >>> X_train, X_test = X[:50], X[50:]
    >>> Y_train, Y_test = Y[:50], Y[50:]
    >>>
    >>> views = [X_train, Y_train]
    >>> test_views = [X_test, Y_test]
    >>>
    >>> # Train an MCCA Model
    >>> # -------------------
    >>> mcca = MCCA(latent_dimensions=2)
    >>> mcca.fit(views)
    >>>
    >>> # %%
    >>> # Plotting the Covariance Heatmap
    >>> # -------------------------------
    >>> CovarianceHeatmapDisplay.from_estimator(mcca, views, test_views=test_views).plot()
    >>> plt.show()

    """

    def __init__(self, train_covariances, test_covariances):
        self.train_covariances = train_covariances
        self.test_covariances = test_covariances

    @classmethod
    def from_estimator(cls, model, train_views, test_views=None):
        train_scores = model.transform(train_views)
        if test_views is not None:
            test_scores = model.transform(test_views)
        else:
            test_scores = None
        train_covariances = np.cov(train_scores[0].T, train_scores[1].T)
        if test_scores is not None:
            test_covariances = np.cov(test_scores[0].T, test_scores[1].T)
        else:
            test_covariances = None
        return cls.from_covariances(train_covariances, test_covariances)

    @classmethod
    def from_covariances(cls, train_covariances, test_covariances=None):
        return cls(train_covariances, test_covariances)

    def plot(self):
        fig, axs = plt.subplots(1, 2, figsize=(10, 5))
        sns.heatmap(
            self.train_covariances,
            annot=True,
            cmap="coolwarm",
            ax=axs[0],
        )
        if self.test_covariances is not None:
            sns.heatmap(
                self.test_covariances,
                annot=True,
                cmap="coolwarm",
                ax=axs[1],
            )
        axs[0].set_title("Train Covariances")
        axs[1].set_title("Test Covariances")
        plt.tight_layout()
        self.figure_ = fig
        return self
