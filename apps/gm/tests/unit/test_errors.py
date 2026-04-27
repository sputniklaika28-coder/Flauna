from __future__ import annotations

from tacex_gm.errors import CloseCode, ErrorCode


class TestErrorCode:
    def test_is_str_enum(self):
        assert isinstance(ErrorCode.INTERNAL_ERROR, str)
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"

    def test_auth_codes(self):
        assert ErrorCode.AUTH_INVALID_TOKEN == "AUTH_INVALID_TOKEN"
        assert ErrorCode.AUTH_TOKEN_EXPIRED == "AUTH_TOKEN_EXPIRED"
        assert ErrorCode.AUTH_PERMISSION_DENIED == "AUTH_PERMISSION_DENIED"

    def test_room_codes(self):
        assert ErrorCode.ROOM_NOT_FOUND == "ROOM_NOT_FOUND"
        assert ErrorCode.ROOM_FULL == "ROOM_FULL"
        assert ErrorCode.DUPLICATE_CONNECTION == "DUPLICATE_CONNECTION"

    def test_state_machine_codes(self):
        assert ErrorCode.STATE_LOCK_TIMEOUT == "STATE_LOCK_TIMEOUT"
        assert ErrorCode.OUT_OF_TURN == "OUT_OF_TURN"
        assert ErrorCode.INVALID_STATE_TRANSITION == "INVALID_STATE_TRANSITION"
        assert ErrorCode.VERSION_MISMATCH == "VERSION_MISMATCH"

    def test_command_validation_codes(self):
        assert ErrorCode.INVALID_PATH == "INVALID_PATH"
        assert ErrorCode.OUT_OF_RANGE == "OUT_OF_RANGE"
        assert ErrorCode.UNKNOWN_TARGET == "UNKNOWN_TARGET"
        assert ErrorCode.UNKNOWN_CHARACTER == "UNKNOWN_CHARACTER"
        assert ErrorCode.UNKNOWN_WEAPON == "UNKNOWN_WEAPON"
        assert ErrorCode.INVALID_DICE_DISTRIBUTION == "INVALID_DICE_DISTRIBUTION"
        assert ErrorCode.INVALID_ACTION_SEQUENCE == "INVALID_ACTION_SEQUENCE"
        assert ErrorCode.INVALID_MESSAGE == "INVALID_MESSAGE"

    def test_resource_codes(self):
        assert ErrorCode.INSUFFICIENT_MP == "INSUFFICIENT_MP"
        assert ErrorCode.INSUFFICIENT_KATASHIRO == "INSUFFICIENT_KATASHIRO"
        assert ErrorCode.NO_LINE_OF_SIGHT == "NO_LINE_OF_SIGHT"

    def test_interrupt_codes(self):
        assert ErrorCode.PENDING_NOT_FOUND == "PENDING_NOT_FOUND"
        assert ErrorCode.PENDING_EXPIRED == "PENDING_EXPIRED"
        assert ErrorCode.DUPLICATE_REQUEST == "DUPLICATE_REQUEST"

    def test_ai_codes(self):
        assert ErrorCode.AI_FALLBACK == "AI_FALLBACK"
        assert ErrorCode.AI_PARSE_ERROR == "AI_PARSE_ERROR"
        assert ErrorCode.AI_BACKEND_UNAVAILABLE == "AI_BACKEND_UNAVAILABLE"

    def test_scenario_codes(self):
        assert ErrorCode.SCENARIO_VALIDATION_FAILED == "SCENARIO_VALIDATION_FAILED"
        assert ErrorCode.SCENARIO_NOT_FOUND == "SCENARIO_NOT_FOUND"

    def test_all_values_are_unique(self):
        values = [e.value for e in ErrorCode]
        assert len(values) == len(set(values))


class TestCloseCode:
    def test_normal(self):
        assert CloseCode.NORMAL == 1000

    def test_client_leaving(self):
        assert CloseCode.CLIENT_LEAVING == 1001

    def test_auth_failed(self):
        assert CloseCode.AUTH_FAILED == 4000

    def test_session_lost_codes(self):
        assert CloseCode.SESSION_LOST_TIMEOUT == 4001
        assert CloseCode.SESSION_LOST_RESTART == 4002

    def test_rate_and_pressure_codes(self):
        assert CloseCode.BACK_PRESSURE == 4003
        assert CloseCode.RATE_LIMITED == 4004
        assert CloseCode.DUPLICATE_CONNECTION == 4005

    def test_all_values_are_unique(self):
        attrs = [v for k, v in vars(CloseCode).items() if not k.startswith("_")]
        assert len(attrs) == len(set(attrs))
