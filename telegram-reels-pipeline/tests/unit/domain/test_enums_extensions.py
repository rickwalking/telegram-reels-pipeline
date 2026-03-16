"""Tests for new domain enum extensions — TriggerSource and RunExecutionStatus."""

from __future__ import annotations

from pipeline.domain.enums import RunExecutionStatus, TriggerSource


class TestTriggerSource:
    def test_has_all_expected_members(self) -> None:
        # Arrange
        expected_member_names = {"WEB_UI", "TELEGRAM_BOT", "CI_WEBHOOK", "API_CLIENT", "CLI"}

        # Act
        actual_member_names = {member.name for member in TriggerSource}

        # Assert
        assert actual_member_names == expected_member_names

    def test_member_count_is_five(self) -> None:
        # Arrange / Act / Assert
        assert len(TriggerSource) == 5

    def test_web_ui_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert TriggerSource.WEB_UI.value == "web_ui"

    def test_telegram_bot_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert TriggerSource.TELEGRAM_BOT.value == "telegram_bot"

    def test_ci_webhook_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert TriggerSource.CI_WEBHOOK.value == "ci_webhook"

    def test_api_client_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert TriggerSource.API_CLIENT.value == "api_client"

    def test_cli_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert TriggerSource.CLI.value == "cli"

    def test_all_values_are_unique(self) -> None:
        # Arrange
        all_values = [member.value for member in TriggerSource]

        # Act
        unique_values = set(all_values)

        # Assert
        assert len(all_values) == len(unique_values)

    def test_all_values_are_lowercase_snake_case(self) -> None:
        # Arrange / Act / Assert
        for member in TriggerSource:
            assert member.value == member.value.lower(), f"{member.name} value should be lowercase"
            assert " " not in member.value, f"{member.name} value should not contain spaces"


class TestRunExecutionStatus:
    def test_has_all_expected_members(self) -> None:
        # Arrange
        expected_member_names = {"PENDING", "IN_PROGRESS", "COMPLETED", "FAILED", "PAUSED", "CANCELLED"}

        # Act
        actual_member_names = {member.name for member in RunExecutionStatus}

        # Assert
        assert actual_member_names == expected_member_names

    def test_member_count_is_six(self) -> None:
        # Arrange / Act / Assert
        assert len(RunExecutionStatus) == 6

    def test_pending_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.PENDING.value == "pending"

    def test_in_progress_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.COMPLETED.value == "completed"

    def test_failed_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.FAILED.value == "failed"

    def test_paused_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.PAUSED.value == "paused"

    def test_cancelled_value_is_correct_string(self) -> None:
        # Arrange / Act / Assert
        assert RunExecutionStatus.CANCELLED.value == "cancelled"

    def test_all_values_are_unique(self) -> None:
        # Arrange
        all_values = [member.value for member in RunExecutionStatus]

        # Act
        unique_values = set(all_values)

        # Assert
        assert len(all_values) == len(unique_values)

    def test_all_values_are_lowercase_snake_case(self) -> None:
        # Arrange / Act / Assert
        for member in RunExecutionStatus:
            assert member.value == member.value.lower(), f"{member.name} value should be lowercase"
            assert " " not in member.value, f"{member.name} value should not contain spaces"
