DO LANGUAGE 'plpgsql'
$$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'stddevis' 
        AND column_name = 'cedeao'
    ) THEN
        ALTER TABLE public.stddevis 
        ALTER COLUMN cedeao 
        DROP DEFAULT;
        
        RAISE NOTICE 'Default value dropped from column.';
    ELSE
        RAISE NOTICE 'Column does not exist. Skipping.';
    END IF;

    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'stdcontrat' 
        AND column_name = 'cedeao'
    ) THEN
        ALTER TABLE public.stdcontrat 
        ALTER COLUMN cedeao 
        DROP DEFAULT;
        
        RAISE NOTICE 'Default value dropped from column.';
    ELSE
        RAISE NOTICE 'Column does not exist. Skipping.';
    END IF;
END;
$$