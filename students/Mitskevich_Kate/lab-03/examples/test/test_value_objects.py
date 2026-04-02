def test_money_creation():
    money = Money(Decimal("100.50"), "RUB")
    assert money.amount == Decimal("100.50")
    assert money.currency == "RUB"

def test_money_cannot_be_negative():
    with pytest.raises(ValueError, match="не может быть отрицательной"):
        Money(Decimal("-10"), "RUB")

def test_transaction_id_format():
    tx_id = TransactionId("TXN-2024-00042")
    assert tx_id.year == 2024
    assert tx_id.number == 42