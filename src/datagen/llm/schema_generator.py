"""LLM-based schema generator with validation loop and auto-repair."""

import json
import logging
from typing import Optional, Tuple
from anthropic import Anthropic
from pydantic import ValidationError

from datagen.core.schema import validate_schema, Dataset
from datagen.llm.prompts import (
    get_system_prompt,
    get_user_prompt,
    get_repair_prompt,
)

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """LLM-based schema generator with validation and auto-repair."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        max_tokens: int = 4096,
    ):
        """
        Initialize schema generator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use
            max_retries: Maximum repair attempts on validation errors
            max_tokens: Maximum tokens for generation
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.max_tokens = max_tokens

    def generate(self, description: str) -> Tuple[dict, Dataset]:
        """
        Generate schema from natural language description.

        Args:
            description: Natural language description of dataset

        Returns:
            Tuple of (schema_dict, validated_dataset)

        Raises:
            ValueError: If schema generation fails after max retries
        """
        logger.info(f"Generating schema from description: {description}")

        # Initial generation
        schema_json = self._call_llm(
            system_prompt=get_system_prompt(),
            user_prompt=get_user_prompt(description),
        )

        # Validation loop with auto-repair
        for attempt in range(self.max_retries + 1):
            try:
                # Parse JSON
                schema_dict = json.loads(schema_json)

                # Validate with Pydantic
                dataset = validate_schema(schema_dict)

                logger.info(f"✓ Schema validated successfully on attempt {attempt + 1}")
                return schema_dict, dataset

            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt + 1}: JSON parse error: {e}")
                if attempt < self.max_retries:
                    schema_json = self._repair_schema(
                        schema_json, f"JSON parse error: {e}"
                    )
                else:
                    raise ValueError(
                        f"Failed to generate valid JSON after {self.max_retries} retries"
                    ) from e

            except ValidationError as e:
                logger.warning(f"Attempt {attempt + 1}: Validation error: {e}")
                if attempt < self.max_retries:
                    schema_json = self._repair_schema(schema_json, str(e))
                else:
                    raise ValueError(
                        f"Failed to generate valid schema after {self.max_retries} retries: {e}"
                    ) from e

            except Exception as e:
                logger.error(f"Unexpected error during validation: {e}")
                raise ValueError(f"Schema generation failed: {e}") from e

        raise ValueError("Schema generation failed after all retries")

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Claude API to generate schema.

        Args:
            system_prompt: System prompt defining role and rules
            user_prompt: User prompt with description or repair instructions

        Returns:
            Generated schema as JSON string
        """
        logger.debug(f"Calling {self.model} with {len(user_prompt)} char prompt")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text from response
        content = response.content[0].text

        # Clean markdown code blocks if present
        if content.startswith("```"):
            # Remove opening ```json or ```
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            # Remove closing ```
            content = content.rsplit("```", 1)[0] if "```" in content else content

        return content.strip()

    def _repair_schema(self, schema_json: str, errors: str) -> str:
        """
        Attempt to repair schema using LLM.

        Args:
            schema_json: Invalid schema JSON
            errors: Validation error messages

        Returns:
            Repaired schema as JSON string
        """
        logger.info("Attempting auto-repair with LLM...")

        repair_prompt = get_repair_prompt(schema_json, errors)

        return self._call_llm(
            system_prompt=get_system_prompt(), user_prompt=repair_prompt
        )


def generate_schema_from_description(
    description: str,
    api_key: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    max_retries: int = 3,
) -> Tuple[dict, Dataset]:
    """
    Generate schema from natural language description.

    Convenience function for one-shot schema generation.

    Args:
        description: Natural language description of dataset
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        model: Claude model to use
        max_retries: Maximum repair attempts on validation errors

    Returns:
        Tuple of (schema_dict, validated_dataset)

    Example:
        >>> schema_dict, dataset = generate_schema_from_description(
        ...     "E-commerce with users, products, and orders"
        ... )
        >>> print(dataset.metadata.name)
        E-commerce Dataset
    """
    generator = SchemaGenerator(api_key=api_key, model=model, max_retries=max_retries)
    return generator.generate(description)
