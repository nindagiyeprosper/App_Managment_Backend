--
-- PostgreSQL database dump
--

\restrict 96SKMOtkmUrMFb6fewtfl3pbntNuhzxtgIORMtI3RE6W6OI2Ljbd0OsA7hled4H

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: statut_commission; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.statut_commission AS ENUM (
    'calculee',
    'validee',
    'payee',
    'annulee'
);


ALTER TYPE public.statut_commission OWNER TO postgres;

--
-- Name: statut_vente; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.statut_vente AS ENUM (
    'payee',
    'annulee'
);


ALTER TYPE public.statut_vente OWNER TO postgres;

--
-- Name: type_mouvement; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.type_mouvement AS ENUM (
    'entree',
    'sortie'
);


ALTER TYPE public.type_mouvement OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: clients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clients (
    id integer NOT NULL,
    nom character varying NOT NULL,
    telephone character varying NOT NULL,
    email character varying,
    adresse character varying,
    password_hash character varying NOT NULL,
    code_parrainage character varying NOT NULL,
    parrain_id integer,
    nb_descendants integer,
    role character varying,
    date_inscription timestamp without time zone
);


ALTER TABLE public.clients OWNER TO postgres;

--
-- Name: clients_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.clients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clients_id_seq OWNER TO postgres;

--
-- Name: clients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.clients_id_seq OWNED BY public.clients.id;


--
-- Name: commissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.commissions (
    id integer NOT NULL,
    vente_id integer NOT NULL,
    beneficiaire_id integer NOT NULL,
    niveau integer NOT NULL,
    taux numeric(5,2) NOT NULL,
    montant numeric(12,2) NOT NULL,
    statut public.statut_commission,
    date_calcul timestamp without time zone,
    date_validation timestamp without time zone,
    date_paiement timestamp without time zone
);


ALTER TABLE public.commissions OWNER TO postgres;

--
-- Name: commissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.commissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.commissions_id_seq OWNER TO postgres;

--
-- Name: commissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.commissions_id_seq OWNED BY public.commissions.id;


--
-- Name: lignes_vente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lignes_vente (
    id integer NOT NULL,
    vente_id integer NOT NULL,
    produit_id integer NOT NULL,
    quantite integer NOT NULL,
    prix_unitaire numeric(12,2) NOT NULL,
    sous_total numeric(12,2) NOT NULL,
    benefice_ligne numeric(12,2) NOT NULL
);


ALTER TABLE public.lignes_vente OWNER TO postgres;

--
-- Name: lignes_vente_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lignes_vente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lignes_vente_id_seq OWNER TO postgres;

--
-- Name: lignes_vente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lignes_vente_id_seq OWNED BY public.lignes_vente.id;


--
-- Name: mouvements_stock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mouvements_stock (
    id integer NOT NULL,
    produit_id integer NOT NULL,
    type public.type_mouvement NOT NULL,
    quantite integer NOT NULL,
    motif character varying,
    date timestamp without time zone,
    admin_id integer
);


ALTER TABLE public.mouvements_stock OWNER TO postgres;

--
-- Name: mouvements_stock_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mouvements_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mouvements_stock_id_seq OWNER TO postgres;

--
-- Name: mouvements_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mouvements_stock_id_seq OWNED BY public.mouvements_stock.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    client_id integer NOT NULL,
    type character varying NOT NULL,
    message character varying NOT NULL,
    lu boolean,
    date timestamp without time zone
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO postgres;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: paiements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paiements (
    id integer NOT NULL,
    client_id integer NOT NULL,
    montant numeric(12,2) NOT NULL,
    date timestamp without time zone,
    reference character varying NOT NULL,
    admin_id integer,
    notes character varying
);


ALTER TABLE public.paiements OWNER TO postgres;

--
-- Name: paiements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.paiements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.paiements_id_seq OWNER TO postgres;

--
-- Name: paiements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.paiements_id_seq OWNED BY public.paiements.id;


--
-- Name: produits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.produits (
    id integer NOT NULL,
    nom character varying NOT NULL,
    categorie character varying NOT NULL,
    taille character varying,
    couleur character varying,
    prix_achat numeric(12,2) NOT NULL,
    prix_vente numeric(12,2) NOT NULL,
    stock integer,
    seuil_alerte integer,
    actif boolean
);


ALTER TABLE public.produits OWNER TO postgres;

--
-- Name: produits_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.produits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.produits_id_seq OWNER TO postgres;

--
-- Name: produits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.produits_id_seq OWNED BY public.produits.id;


--
-- Name: ventes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ventes (
    id integer NOT NULL,
    client_id integer NOT NULL,
    date timestamp without time zone,
    montant_total numeric(12,2) NOT NULL,
    benefice_total numeric(12,2) NOT NULL,
    statut public.statut_vente
);


ALTER TABLE public.ventes OWNER TO postgres;

--
-- Name: ventes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ventes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ventes_id_seq OWNER TO postgres;

--
-- Name: ventes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ventes_id_seq OWNED BY public.ventes.id;


--
-- Name: clients id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clients ALTER COLUMN id SET DEFAULT nextval('public.clients_id_seq'::regclass);


--
-- Name: commissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commissions ALTER COLUMN id SET DEFAULT nextval('public.commissions_id_seq'::regclass);


--
-- Name: lignes_vente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lignes_vente ALTER COLUMN id SET DEFAULT nextval('public.lignes_vente_id_seq'::regclass);


--
-- Name: mouvements_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mouvements_stock ALTER COLUMN id SET DEFAULT nextval('public.mouvements_stock_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: paiements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiements ALTER COLUMN id SET DEFAULT nextval('public.paiements_id_seq'::regclass);


--
-- Name: produits id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.produits ALTER COLUMN id SET DEFAULT nextval('public.produits_id_seq'::regclass);


--
-- Name: ventes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ventes ALTER COLUMN id SET DEFAULT nextval('public.ventes_id_seq'::regclass);


--
-- Data for Name: clients; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.clients (id, nom, telephone, email, adresse, password_hash, code_parrainage, parrain_id, nb_descendants, role, date_inscription) FROM stdin;
1	NINDAGIYE Prosper	+25767895912	nindagiyeprosper@gmail.com	Bujumbura	$2b$12$vzlV/V7kQdvFwQye0KFgxOMEv9qDf3Bv1UtWvo6V1sJE24PNUZgCu	AVNAXAR0	\N	1	admin	2026-10-21 00:39:46.603614
2	Ninziza	+25767123456	ninziza@gmail.com	Bujumbura	$2b$12$LP64HPKbVUO2YbGePUHRuOqzDoaCrqVrEeMu5SH9xv6ry8JWLLtY6	8PBJLYO	1	0	client	2026-10-21 01:11:07.924407
3	NINDAGIYE Prosper	+25767895911	nindagiyeprosper@gmail.com	Bujumbura	$2b$12$YV.US3aNw5NABWK6ZwQox.IoU515C1nNp//12tZYdVjfUtmubU3Gu	KLZXED3A	\N	0	client	2026-10-21 02:15:48.869466
4	HIMBAZIMANA	+25765266216	himbazimana@gmail.com	\N	$2b$12$iC2nRgow1YN1jGaiWu1kt.F2nEt5X6EtcBStugARPXV2fQbqMvoES	DFPEASWR	\N	0	client	2026-10-21 18:57:49.289483
\.


--
-- Data for Name: commissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.commissions (id, vente_id, beneficiaire_id, niveau, taux, montant, statut, date_calcul, date_validation, date_paiement) FROM stdin;
\.


--
-- Data for Name: lignes_vente; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.lignes_vente (id, vente_id, produit_id, quantite, prix_unitaire, sous_total, benefice_ligne) FROM stdin;
1	1	1	1	1600.00	1600.00	0.00
\.


--
-- Data for Name: mouvements_stock; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.mouvements_stock (id, produit_id, type, quantite, motif, date, admin_id) FROM stdin;
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notifications (id, client_id, type, message, lu, date) FROM stdin;
1	1	parrainage	Nouveau filleul : Ninziza	t	2026-10-21 01:11:07.958051
\.


--
-- Data for Name: paiements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.paiements (id, client_id, montant, date, reference, admin_id, notes) FROM stdin;
\.


--
-- Data for Name: produits; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.produits (id, nom, categorie, taille, couleur, prix_achat, prix_vente, stock, seuil_alerte, actif) FROM stdin;
1	Ipapa	supres	\N	\N	1600.00	1600.00	0	5	f
\.


--
-- Data for Name: ventes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ventes (id, client_id, date, montant_total, benefice_total, statut) FROM stdin;
1	1	2026-10-21 00:58:59.667733	1600.00	0.00	payee
\.


--
-- Name: clients_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.clients_id_seq', 4, true);


--
-- Name: commissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.commissions_id_seq', 1, false);


--
-- Name: lignes_vente_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.lignes_vente_id_seq', 2, false);


--
-- Name: mouvements_stock_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.mouvements_stock_id_seq', 1, false);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notifications_id_seq', 2, false);


--
-- Name: paiements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.paiements_id_seq', 1, false);


--
-- Name: produits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.produits_id_seq', 2, false);


--
-- Name: ventes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ventes_id_seq', 2, false);


--
-- Name: clients clients_code_parrainage_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_code_parrainage_key UNIQUE (code_parrainage);


--
-- Name: clients clients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_pkey PRIMARY KEY (id);


--
-- Name: clients clients_telephone_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_telephone_key UNIQUE (telephone);


--
-- Name: commissions commissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commissions
    ADD CONSTRAINT commissions_pkey PRIMARY KEY (id);


--
-- Name: lignes_vente lignes_vente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lignes_vente
    ADD CONSTRAINT lignes_vente_pkey PRIMARY KEY (id);


--
-- Name: mouvements_stock mouvements_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mouvements_stock
    ADD CONSTRAINT mouvements_stock_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: paiements paiements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiements
    ADD CONSTRAINT paiements_pkey PRIMARY KEY (id);


--
-- Name: produits produits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.produits
    ADD CONSTRAINT produits_pkey PRIMARY KEY (id);


--
-- Name: ventes ventes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ventes
    ADD CONSTRAINT ventes_pkey PRIMARY KEY (id);


--
-- Name: clients clients_parrain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clients
    ADD CONSTRAINT clients_parrain_id_fkey FOREIGN KEY (parrain_id) REFERENCES public.clients(id);


--
-- Name: commissions commissions_beneficiaire_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commissions
    ADD CONSTRAINT commissions_beneficiaire_id_fkey FOREIGN KEY (beneficiaire_id) REFERENCES public.clients(id);


--
-- Name: commissions commissions_vente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.commissions
    ADD CONSTRAINT commissions_vente_id_fkey FOREIGN KEY (vente_id) REFERENCES public.ventes(id);


--
-- Name: lignes_vente lignes_vente_produit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lignes_vente
    ADD CONSTRAINT lignes_vente_produit_id_fkey FOREIGN KEY (produit_id) REFERENCES public.produits(id);


--
-- Name: lignes_vente lignes_vente_vente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lignes_vente
    ADD CONSTRAINT lignes_vente_vente_id_fkey FOREIGN KEY (vente_id) REFERENCES public.ventes(id);


--
-- Name: mouvements_stock mouvements_stock_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mouvements_stock
    ADD CONSTRAINT mouvements_stock_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.clients(id);


--
-- Name: mouvements_stock mouvements_stock_produit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mouvements_stock
    ADD CONSTRAINT mouvements_stock_produit_id_fkey FOREIGN KEY (produit_id) REFERENCES public.produits(id);


--
-- Name: notifications notifications_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: paiements paiements_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiements
    ADD CONSTRAINT paiements_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.clients(id);


--
-- Name: paiements paiements_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paiements
    ADD CONSTRAINT paiements_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- Name: ventes ventes_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ventes
    ADD CONSTRAINT ventes_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.clients(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 96SKMOtkmUrMFb6fewtfl3pbntNuhzxtgIORMtI3RE6W6OI2Ljbd0OsA7hled4H

