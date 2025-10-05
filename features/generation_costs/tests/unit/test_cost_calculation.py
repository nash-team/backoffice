"""Unit tests for CostCalculation value object."""

from decimal import Decimal

from backoffice.features.generation_costs.domain.entities.cost_calculation import CostCalculation
from backoffice.features.generation_costs.domain.entities.token_usage import ImageUsage, TokenUsage


class TestCostCalculation:
    """Test suite for CostCalculation value object."""

    def test_total_cost_with_token_usages(self):
        """Test total cost calculation with token usages."""
        # Given
        usages = [
            TokenUsage(
                model="gpt-4", prompt_tokens=100, completion_tokens=50, cost=Decimal("0.01")
            ),
            TokenUsage(
                model="gpt-4", prompt_tokens=200, completion_tokens=100, cost=Decimal("0.02")
            ),
        ]
        calculation = CostCalculation(request_id="req1", token_usages=usages)

        # When/Then
        assert calculation.total_cost == Decimal("0.03")

    def test_total_cost_with_image_usages(self):
        """Test total cost calculation with image usages."""
        # Given
        usages = [
            ImageUsage(model="dalle-3", input_images=0, output_images=1, cost=Decimal("0.04")),
            ImageUsage(model="dalle-3", input_images=0, output_images=1, cost=Decimal("0.04")),
        ]
        calculation = CostCalculation(request_id="req1", image_usages=usages)

        # When/Then
        assert calculation.total_cost == Decimal("0.08")

    def test_total_cost_with_mixed_usages(self):
        """Test total cost calculation with both token and image usages."""
        # Given
        token_usages = [
            TokenUsage(model="gpt-4", prompt_tokens=100, completion_tokens=50, cost=Decimal("0.01"))
        ]
        image_usages = [
            ImageUsage(model="dalle-3", input_images=0, output_images=1, cost=Decimal("0.04"))
        ]
        calculation = CostCalculation(
            request_id="req1", token_usages=token_usages, image_usages=image_usages
        )

        # When/Then
        assert calculation.total_cost == Decimal("0.05")

    def test_total_tokens(self):
        """Test total tokens calculation."""
        # Given
        usages = [
            TokenUsage(
                model="gpt-4", prompt_tokens=100, completion_tokens=50, cost=Decimal("0.01")
            ),
            TokenUsage(
                model="gpt-4", prompt_tokens=200, completion_tokens=100, cost=Decimal("0.02")
            ),
        ]
        calculation = CostCalculation(request_id="req1", token_usages=usages)

        # When/Then
        assert calculation.total_prompt_tokens == 300
        assert calculation.total_completion_tokens == 150
        assert calculation.total_tokens == 450

    def test_api_call_count(self):
        """Test API call count calculation."""
        # Given
        token_usages = [
            TokenUsage(
                model="gpt-4", prompt_tokens=100, completion_tokens=50, cost=Decimal("0.01")
            ),
            TokenUsage(
                model="gpt-4", prompt_tokens=200, completion_tokens=100, cost=Decimal("0.02")
            ),
        ]
        image_usages = [
            ImageUsage(model="dalle-3", input_images=0, output_images=1, cost=Decimal("0.04"))
        ]
        calculation = CostCalculation(
            request_id="req1", token_usages=token_usages, image_usages=image_usages
        )

        # When/Then
        assert calculation.api_call_count == 3

    def test_average_cost_per_call(self):
        """Test average cost per call calculation."""
        # Given
        usages = [
            TokenUsage(
                model="gpt-4", prompt_tokens=100, completion_tokens=50, cost=Decimal("0.01")
            ),
            TokenUsage(
                model="gpt-4", prompt_tokens=200, completion_tokens=100, cost=Decimal("0.02")
            ),
        ]
        calculation = CostCalculation(request_id="req1", token_usages=usages)

        # When/Then
        assert calculation.average_cost_per_call == Decimal("0.015")

    def test_average_cost_per_call_with_zero_calls(self):
        """Test average cost per call with zero API calls."""
        # Given
        calculation = CostCalculation(request_id="req1")

        # When/Then
        assert calculation.average_cost_per_call == Decimal("0")

    def test_empty_calculation(self):
        """Test empty cost calculation."""
        # Given
        calculation = CostCalculation(request_id="req1")

        # When/Then
        assert calculation.total_cost == Decimal("0")
        assert calculation.total_tokens == 0
        assert calculation.api_call_count == 0
