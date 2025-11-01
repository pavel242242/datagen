"""Semantic generators: Faker adapter with locale support."""

import numpy as np
from faker import Faker
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Default locale mapping (country code -> Faker locale)
DEFAULT_LOCALE_MAP = {
    "US": "en_US",
    "UK": "en_GB",
    "GB": "en_GB",
    "DE": "de_DE",
    "FR": "fr_FR",
    "ES": "es_ES",
    "IT": "it_IT",
    "JP": "ja_JP",
    "CN": "zh_CN",
    "KR": "ko_KR",
    "BR": "pt_BR",
    "IN": "en_IN",
    "MX": "es_MX",
    "CA": "en_CA",
    "AU": "en_AU",
    "NL": "nl_NL",
    "SE": "sv_SE",
    "NO": "nb_NO",
    "DK": "da_DK",
    "FI": "fi_FI",
    "PL": "pl_PL",
    "RU": "ru_RU",
    "TR": "tr_TR",
    "CZ": "cs_CZ",
    "Prague": "cs_CZ",  # City mappings
    "Brno": "cs_CZ",
    "Ostrava": "cs_CZ",
    "Plzen": "cs_CZ",
}


def resolve_locale(country_or_city: str) -> str:
    """
    Resolve country/city code to Faker locale.

    Args:
        country_or_city: Country code (e.g., "US") or city name

    Returns:
        Faker locale string (e.g., "en_US")

    Examples:
        >>> resolve_locale("US")
        'en_US'
        >>> resolve_locale("Prague")
        'cs_CZ'
        >>> resolve_locale("Unknown")
        'en_US'
    """
    # Try exact match
    locale = DEFAULT_LOCALE_MAP.get(country_or_city)

    if locale:
        return locale

    # Fallback to en_US
    logger.debug(f"No locale mapping for '{country_or_city}', using en_US")
    return "en_US"


class FakerAdapter:
    """
    Adapter for Faker with caching and batching.

    Faker can be slow for large datasets, so we:
    - Cache Faker instances per locale
    - Support batch generation with seed per batch
    """

    def __init__(self):
        self._faker_cache = {}

    def get_faker(self, locale: str = "en_US") -> Faker:
        """Get or create Faker instance for locale."""
        if locale not in self._faker_cache:
            self._faker_cache[locale] = Faker(locale)
        return self._faker_cache[locale]

    def generate(
        self,
        method: str,
        size: int,
        rng: np.random.Generator,
        locale: str = "en_US",
        **kwargs
    ) -> np.ndarray:
        """
        Generate fake data using Faker method.

        Args:
            method: Faker method name (e.g., "name", "email", "address")
            size: Number of values to generate
            rng: Random generator (used for seeding Faker)
            locale: Faker locale
            **kwargs: Additional arguments to Faker method

        Returns:
            Array of generated values

        Examples:
            >>> adapter = FakerAdapter()
            >>> rng = np.random.default_rng(42)
            >>> names = adapter.generate("name", 5, rng, locale="en_US")
            >>> len(names)
            5
        """
        faker = self.get_faker(locale)

        # Seed Faker with a value from rng for reproducibility
        faker.seed_instance(int(rng.integers(0, 2**31)))

        # Check if method exists
        if not hasattr(faker, method):
            raise ValueError(f"Faker has no method '{method}'")

        # Generate values
        func = getattr(faker, method)
        values = [func(**kwargs) for _ in range(size)]

        return np.array(values)


# Global adapter instance
_faker_adapter = FakerAdapter()


def generate_faker(
    method: str,
    size: int,
    rng: np.random.Generator,
    locale: Optional[str] = None,
    locale_from_values: Optional[np.ndarray] = None,
    **kwargs
) -> np.ndarray:
    """
    Generate semantic data using Faker.

    Args:
        method: Faker method (e.g., "name", "email", "address")
        size: Number of values
        rng: Random generator
        locale: Fixed locale string, or None
        locale_from_values: Array of country/city values to derive locales from
        **kwargs: Additional Faker method arguments

    Returns:
        Array of generated values

    Examples:
        >>> rng = np.random.default_rng(42)
        >>> emails = generate_faker("email", 3, rng)
        >>> len(emails)
        3

        >>> countries = np.array(["US", "DE", "FR"])
        >>> names = generate_faker("name", 3, rng, locale_from_values=countries)
        >>> len(names)
        3
    """
    if locale_from_values is not None:
        # Generate per-locale
        if len(locale_from_values) != size:
            raise ValueError(
                f"locale_from_values length ({len(locale_from_values)}) "
                f"must match size ({size})"
            )

        result = []
        for country in locale_from_values:
            loc = resolve_locale(str(country))
            # Generate one value for this locale
            val = _faker_adapter.generate(method, 1, rng, locale=loc, **kwargs)[0]
            result.append(val)

        return np.array(result)

    else:
        # Single locale for all
        if locale is None:
            locale = "en_US"

        return _faker_adapter.generate(method, size, rng, locale=locale, **kwargs)
