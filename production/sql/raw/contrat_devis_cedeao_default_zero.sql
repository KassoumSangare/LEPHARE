ALTER TABLE public.stddevis ALTER COLUMN cedeao SET DEFAULT 0;

ALTER TABLE public.stdcontrat ALTER COLUMN cedeao SET DEFAULT 0;


DO LANGUAGE 'plpgsql'
$$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'stddevis' 
        AND column_name = 'cedeao'
        AND column_default IS NULL  
    ) THEN
        ALTER TABLE public.stddevis 
        ALTER COLUMN cedeao 
        SET DEFAULT 0;
    END IF;


    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'stdcontrat' 
        AND column_name = 'cedeao'
        AND column_default IS NULL  
    ) THEN
        ALTER TABLE public.stdcontrat 
        ALTER COLUMN cedeao 
        SET DEFAULT 0;
    END IF;
END;
$$