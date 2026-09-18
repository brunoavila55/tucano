ALTER TABLE portfolio_items
    DROP CONSTRAINT portfolio_items_storage_key_format,
    ADD CONSTRAINT portfolio_items_storage_key_format
        CHECK (storage_key ~ '^[a-f0-9-]+\\.(jpg|png)$');
