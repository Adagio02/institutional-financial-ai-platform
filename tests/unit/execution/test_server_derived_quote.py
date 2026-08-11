from finai.api.schemas.order import (
    OrderCreate,
)


def test_order_request_does_not_define_reference_price() -> None:
    assert (
        "reference_price"
        not in OrderCreate.model_fields
    )
def test_order_request_keeps_limit_price() -> None:
    assert (
        "limit_price"
        in OrderCreate.model_fields
    )