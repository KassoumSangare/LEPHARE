CREATE FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date) RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric)
    LANGUAGE plpgsql
    AS $$
DECLARE
	
	duree_contrat integer;

CREATE FUNCTION public.fn_liste_pays_voyage(id_compagnie_ integer) RETURNS TABLE(idpays integer, libellepays character varying, nationalite character varying, idzone integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
	
	RETURN QUERY
		SELECT SP.id_pays, SP.libelle_pays, SP.nationalite, SVP.id_zone
		FROM StdPays AS SP
		INNER JOIN StdZoneVoyagePays AS SVP ON (SP.id_pays = SVP.id_pays)
		INNER JOIN StdZoneVoyage AS SV ON (SVP.id_zone = SV.id_zone)
		WHERE SV.id_compagnie = id_compagnie_
		ORDER BY SP.libelle_pays;

CREATE PROCEDURE public.sp_creation_devis_voyage(IN id_intermediaire integer, IN id_compagnie_p integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_voyage boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN id_pays_destination integer, IN id_pays_voyageur integer, IN reference_contrat character varying, IN numero_attestation character varying, IN visa_schengen boolean, IN numero_passport character varying, IN taux_reduction numeric, IN date_naissance date, IN numero_police_compagnie character varying, INOUT id_devis integer, INOUT out_message character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
	etat_traitement character varying(1); numero_avenant character varying(8); clef_avenant integer; numero_devis varchar(16);code_categorie character varying(3);

