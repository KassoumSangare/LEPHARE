-- Name: fn_garantie_offre_voyage(integer, integer, integer, integer, numeric, date, date, date); Type: FUNCTION; Schema: public; Owner: uranususer
CREATE FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date) RETURNS TABLE(idgarantie integer, libellegarantie character varying, idsousgarantie integer, libellesousgarantie character varying, acquise boolean, capital numeric, nombreplace integer, primeannuelle numeric, primenette numeric, taxe numeric, montantaccessoire numeric)
    LANGUAGE plpgsql
    AS $$
DECLARE
	
	duree_contrat integer;
ALTER FUNCTION public.fn_garantie_offre_voyage(id_compagnie integer, id_tarif integer, id_offre integer, id_zone_voyage integer, taux_reduction numeric, date_effet date, date_expiration date, date_naissance date) OWNER TO uranususer;
-- Name: fn_liste_pays_voyage(integer); Type: FUNCTION; Schema: public; Owner: uranususer
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
ALTER FUNCTION public.fn_liste_pays_voyage(id_compagnie_ integer) OWNER TO uranususer;
-- Name: sp_creation_devis_voyage(integer, integer, integer, integer, integer, integer, integer, boolean, boolean, date, date, date, integer, integer, integer, character varying, character varying, boolean, character varying, numeric, date, character varying, integer, character varying); Type: PROCEDURE; Schema: public; Owner: uranususer
CREATE PROCEDURE public.sp_creation_devis_voyage(IN id_intermediaire integer, IN id_compagnie_p integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_voyage boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN id_pays_destination integer, IN id_pays_voyageur integer, IN reference_contrat character varying, IN numero_attestation character varying, IN visa_schengen boolean, IN numero_passport character varying, IN taux_reduction numeric, IN date_naissance date, IN numero_police_compagnie character varying, INOUT id_devis integer, INOUT out_message character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
	etat_traitement character varying(1); numero_avenant character varying(8); clef_avenant integer; numero_devis varchar(16);code_categorie character varying(3);
	FROM fn_garantie_offre_voyage(id_compagnie_p, id_tarif, id_offre, id_zone_voyage, taux_reduction, date_effet, date_expiration, date_naissance)
	WHERE idgarantie <> 0
	ORDER BY 1;
ALTER PROCEDURE public.sp_creation_devis_voyage(IN id_intermediaire integer, IN id_compagnie_p integer, IN id_produit integer, IN id_offre integer, IN id_avenant integer, IN id_client integer, IN id_assure integer, IN flotte_voyage boolean, IN en_coassurance boolean, IN date_effet date, IN date_expiration date, IN date_emission date, IN id_tarif integer, IN id_pays_destination integer, IN id_pays_voyageur integer, IN reference_contrat character varying, IN numero_attestation character varying, IN visa_schengen boolean, IN numero_passport character varying, IN taux_reduction numeric, IN date_naissance date, IN numero_police_compagnie character varying, INOUT id_devis integer, INOUT out_message character varying) OWNER TO uranususer;
437	production	0124_sp_creation_devis_voyage	2026-05-12 14:22:58.46484+00
438	production	0132_merge_20260512_1350	2026-05-12 14:22:58.478477+00
439	production	0133_certificattransport_accessoire_afs_ci_and_more	2026-05-12 14:22:58.636189+00
440	production	0134_sp_generation_devis_transport_client	2026-05-19 10:09:01.401066+00
441	production	0135_sp_generation_contrat_transport	2026-05-19 10:09:01.708605+00
442	production	0132_sp_avenant_incorporation	2026-05-19 10:09:01.7717+00
443	production	0136_merge_20260519_1004	2026-05-19 10:09:01.797205+00
444	production	0137_sp_avenant_retrait	2026-05-22 07:41:18.549661+00
445	production	0138_sp_finalisation_devis_ia_taxe_arrondi	2026-05-22 07:41:18.596127+00
446	production	0139_fn_get_accessoire_suppression_plus1_offre154	2026-05-22 07:41:18.618568+00
\.


--
-- Data for Name: django_rest_passwordreset_resetpasswordtoken; Type: TABLE DATA; Schema: public; Owner: uranususer
