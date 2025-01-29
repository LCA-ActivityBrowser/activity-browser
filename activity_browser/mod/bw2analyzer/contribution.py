from bw2analyzer import ContributionAnalysis

from typing import Optional
import numpy as np

class ABContributionAnalysis(ContributionAnalysis):
    """Activity Browser version of bw2analyzer.ContributionAnalysis"""
    def sort_array(self, data: np.array, limit: float = 25, limit_type: str = "number", total: Optional[float] = None) -> np.array:
        """Activity Browser version of bw2analyzer.ContributionAnalysis.sort_array.

        Should be removed once https://github.com/brightway-lca/brightway2-analyzer/pull/32 is merged.
        See PR above on why we overwrite this function.
        """
        if not total:
            total = np.abs(data).sum()

        if total == 0 and limit_type == "cum_percent":
            raise ValueError(
                "Cumulative percentage cannot be calculated to a total of 0, use a different limit type or total")

        if limit_type not in ("number", "percent", "cum_percent"):
            raise ValueError(f"limit_type must be either 'number', 'percent' or 'cum_percent' not '{limit_type}'.")
        if limit_type in ("percent", "cum_percent"):
            if not 0 < limit <= 1:
                raise ValueError("Percentage limits > 0 and <= 1.")
        if limit_type == "number":
            if not int(limit) == limit:
                raise ValueError("Number limit must a whole number.")
            if not 0 < limit:
                raise ValueError("Number limit must be < 0.")

        results = np.hstack(
            (data.reshape((-1, 1)), np.arange(data.shape[0]).reshape((-1, 1)))
        )

        if limit_type == "number":
            # sort and cut off at limit
            return results[np.argsort(np.abs(data))[::-1]][:limit, :]
        elif limit_type == "percent":
            # identify good values, drop rest and sort
            limit = (np.abs(data) >= (abs(total) * limit))
            results = results[limit, :]
            return results[np.argsort(np.abs(results[:, 0]))[::-1]]
        elif limit_type == "cum_percent":
            # if we would apply this on the 'correct' order, this would stop just before the limit,
            # we want to be on or the first step over the limit.
            results = results[np.argsort(np.abs(data))]  # sort low to high impact
            cumsum = np.cumsum(np.abs(results[:, 0])) / abs(total)
            limit = (cumsum >= (1 - limit))  # find items under limit
            return results[limit, :][::-1]  # drop items under limit and set correct order
