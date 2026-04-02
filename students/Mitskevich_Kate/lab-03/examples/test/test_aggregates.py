def test_income_transaction_validation():
    dist = [CategoryDistribution("CAT-01", Decimal("600")),
            CategoryDistribution("CAT-02", Decimal("400"))]
    tx = Transaction(
        transaction_id="TXN-2024-00001",
        user_id="user-001",
        type=TransactionType.INCOME,
        amount=Decimal("1000"),
        distributions=dist
    )
    assert tx.status == TransactionStatus.PENDING

def test_invalid_distribution_sum():
    dist = [CategoryDistribution("CAT-01", Decimal("700"))]
    with pytest.raises(ValueError, match="не равна сумме дохода"):
        Transaction(
            transaction_id="TXN-2024-00002",
            user_id="user-001",
            type=TransactionType.INCOME,
            amount=Decimal("1000"),
            distributions=dist
        )