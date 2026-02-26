"""Tests for the bus departure provider and DisplayState bus fields."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.display.state import DisplayState
from src.providers.bus import BusDeparture, fetch_departures, fetch_departures_safe


# --- Helpers ---


def _make_entur_response(calls: list[dict]) -> dict:
    """Build a minimal Entur API response structure."""
    return {
        "data": {
            "quay": {
                "id": "NSR:Quay:73154",
                "name": "Ladeveien",
                "estimatedCalls": calls,
            }
        }
    }


def _make_call(
    dep_time: datetime,
    *,
    realtime: bool = True,
    front_text: str = "Sentrum",
    line_code: str = "4",
    cancellation: bool = False,
) -> dict:
    """Build a single estimatedCall dict matching Entur response format."""
    return {
        "expectedDepartureTime": dep_time.isoformat(),
        "aimedDepartureTime": dep_time.isoformat(),
        "realtime": realtime,
        "cancellation": cancellation,
        "destinationDisplay": {"frontText": front_text},
        "serviceJourney": {"line": {"publicCode": line_code}},
    }


# --- Countdown calculation tests ---


class TestCountdownCalculation:
    """Test that countdown minutes are correctly calculated from ISO 8601 times."""

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_countdown_minutes_calculated_correctly(self, mock_dt, mock_post):
        """Departures 5 and 12 minutes in the future produce correct countdowns."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        dep1 = now + timedelta(minutes=5, seconds=30)  # 5.5 min -> ceil -> 6
        dep2 = now + timedelta(minutes=12, seconds=10)  # 12.17 min -> ceil -> 13

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response(
            [_make_call(dep1), _make_call(dep2)]
        )
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=2)

        assert len(result) == 2
        assert result[0].minutes == 6
        assert result[1].minutes == 13

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_negative_countdown_clamped_to_zero(self, mock_dt, mock_post):
        """A departure in the past is clamped to 0 minutes."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        past_dep = now - timedelta(minutes=2)  # 2 minutes ago

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response(
            [_make_call(past_dep)]
        )
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=1)

        assert len(result) == 1
        assert result[0].minutes == 0

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_one_minute_countdown_for_imminent_departure(self, mock_dt, mock_post):
        """A departure 30 seconds from now shows 1 minute (ceil)."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        imminent = now + timedelta(seconds=30)  # 0.5 min -> ceil -> 1

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response(
            [_make_call(imminent)]
        )
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=1)

        assert result[0].minutes == 1


# --- Cancellation filtering tests ---


class TestCancellationFiltering:
    """Test that cancelled departures are filtered out."""

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_cancelled_departures_are_skipped(self, mock_dt, mock_post):
        """Cancelled departures are excluded from results."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        dep1 = now + timedelta(minutes=5)
        dep2 = now + timedelta(minutes=10)  # cancelled
        dep3 = now + timedelta(minutes=15)

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response([
            _make_call(dep1),
            _make_call(dep2, cancellation=True),
            _make_call(dep3),
        ])
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=3)

        assert len(result) == 2
        assert result[0].minutes == 5
        assert result[1].minutes == 15

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_all_cancelled_returns_empty(self, mock_dt, mock_post):
        """If all departures are cancelled, return empty list."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        dep1 = now + timedelta(minutes=5)
        dep2 = now + timedelta(minutes=10)

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response([
            _make_call(dep1, cancellation=True),
            _make_call(dep2, cancellation=True),
        ])
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=3)

        assert result == []

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_result_limited_to_num_departures(self, mock_dt, mock_post):
        """Non-cancelled results are capped at num_departures."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        calls = [_make_call(now + timedelta(minutes=i * 5)) for i in range(6)]

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response(calls)
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=3)

        assert len(result) == 3


# --- Response parsing tests ---


class TestResponseParsing:
    """Test that Entur API responses are parsed correctly."""

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_empty_estimated_calls_returns_empty_list(self, mock_dt, mock_post):
        """No scheduled departures returns an empty list."""
        now = datetime(2026, 2, 20, 3, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response([])
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73154", num_departures=2)

        assert result == []

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_departure_metadata_parsed(self, mock_dt, mock_post):
        """BusDeparture carries realtime, destination, and line data."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        dep_time = now + timedelta(minutes=7)
        call = _make_call(
            dep_time,
            realtime=True,
            front_text="Strindheim via Lade",
            line_code="6",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response([call])
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures("NSR:Quay:73152", num_departures=1)

        assert len(result) == 1
        assert result[0].is_realtime is True
        assert result[0].destination == "Strindheim via Lade"
        assert result[0].line == "6"
        assert result[0].minutes == 7


# --- Error handling tests ---


class TestErrorHandling:
    """Test that fetch_departures_safe handles errors gracefully."""

    @patch("src.providers.bus.requests.post")
    def test_safe_returns_none_on_connection_error(self, mock_post):
        """Network failure returns None instead of crashing."""
        mock_post.side_effect = ConnectionError("Network unreachable")

        result = fetch_departures_safe("NSR:Quay:73154", num_departures=2)

        assert result is None

    @patch("src.providers.bus.requests.post")
    def test_safe_returns_none_on_timeout(self, mock_post):
        """Timeout returns None instead of crashing."""
        import requests as req

        mock_post.side_effect = req.Timeout("Request timed out")

        result = fetch_departures_safe("NSR:Quay:73154", num_departures=2)

        assert result is None

    @patch("src.providers.bus.requests.post")
    @patch("src.providers.bus.datetime")
    def test_safe_returns_minutes_on_success(self, mock_dt, mock_post):
        """Successful fetch returns list of countdown minutes."""
        now = datetime(2026, 2, 20, 14, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat

        dep1 = now + timedelta(minutes=3)
        dep2 = now + timedelta(minutes=9)

        mock_response = MagicMock()
        mock_response.json.return_value = _make_entur_response(
            [_make_call(dep1), _make_call(dep2)]
        )
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = fetch_departures_safe("NSR:Quay:73154", num_departures=2)

        assert result == [3, 9]


# --- DisplayState bus fields tests ---


class TestDisplayStateBusFields:
    """Test that DisplayState carries bus data and equality works correctly."""

    def test_state_with_bus_data_equality(self):
        """Two states with same bus data are equal."""
        s1 = DisplayState(
            time_str="14:00",
            date_str="tor 20. feb",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
        )
        s2 = DisplayState(
            time_str="14:00",
            date_str="tor 20. feb",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
        )
        assert s1 == s2

    def test_state_with_different_bus_data_not_equal(self):
        """States with different bus data trigger re-render."""
        s1 = DisplayState(
            time_str="14:00",
            date_str="tor 20. feb",
            bus_direction1=(5, 12, 25),
            bus_direction2=(3, 8, 18),
        )
        s2 = DisplayState(
            time_str="14:00",
            date_str="tor 20. feb",
            bus_direction1=(4, 11, 24),
            bus_direction2=(3, 8, 18),
        )
        assert s1 != s2

    def test_state_with_none_bus_data(self):
        """State with no bus data defaults to None."""
        s = DisplayState(time_str="14:00", date_str="tor 20. feb")
        assert s.bus_direction1 is None
        assert s.bus_direction2 is None

    def test_from_now_with_bus_data(self):
        """from_now() converts bus data lists to tuples."""
        dt = datetime(2026, 2, 20, 14, 0, 0)
        bus_data = ([5, 12, 25], [3, 8, 18])
        state = DisplayState.from_now(dt, bus_data=bus_data)

        assert state.bus_direction1 == (5, 12, 25)
        assert state.bus_direction2 == (3, 8, 18)
        assert isinstance(state.bus_direction1, tuple)
        assert isinstance(state.bus_direction2, tuple)

    def test_from_now_with_none_bus_data(self):
        """from_now() handles None bus data gracefully."""
        dt = datetime(2026, 2, 20, 14, 0, 0)
        bus_data = (None, [3, 8])
        state = DisplayState.from_now(dt, bus_data=bus_data)

        assert state.bus_direction1 is None
        assert state.bus_direction2 == (3, 8)

    def test_from_now_default_no_bus_data(self):
        """from_now() without bus_data argument defaults to None."""
        dt = datetime(2026, 2, 20, 14, 0, 0)
        state = DisplayState.from_now(dt)

        assert state.bus_direction1 is None
        assert state.bus_direction2 is None
