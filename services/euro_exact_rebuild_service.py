from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    SWAP_CONFIRMATION,
    build_and_validate_shadows,
    swap_validated_shadows,
)


TARGET_IMPORT_KEYS = (
    "EURO_FRAUD_LOSSES",
    "EURO_RETAIL_INTEREST_RATES",
    "EURO_PAYMENT_SYSTEM_TRANSACTIONS",
)
BUILD_EXACT_CONFIRMATION = "BUILD_EURO_EXACT_V056_SHADOWS"
SWAP_EXACT_CONFIRMATION = "SWAP_EURO_EXACT_V056_SHADOWS"
REBUILD_VERSION = "v056"


def build_exact_shadows(
    engine,
    backup_file,
    confirmation,
    suffix,
    chunk_size=5000,
    insert_batch_size=250,
):
    if confirmation != BUILD_EXACT_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {BUILD_EXACT_CONFIRMATION}"
        )
    return build_and_validate_shadows(
        engine=engine,
        backup_file=backup_file,
        confirmation=BUILD_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        insert_batch_size=insert_batch_size,
        import_keys=TARGET_IMPORT_KEYS,
        version=REBUILD_VERSION,
    )


def swap_exact_shadows(
    engine,
    backup_file,
    confirmation,
    suffix,
    chunk_size=5000,
):
    if confirmation != SWAP_EXACT_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {SWAP_EXACT_CONFIRMATION}"
        )
    return swap_validated_shadows(
        engine=engine,
        backup_file=backup_file,
        confirmation=SWAP_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        import_keys=TARGET_IMPORT_KEYS,
        version=REBUILD_VERSION,
    )
