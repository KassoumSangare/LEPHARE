import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import contratService from './contratService'

const initialState = {
    contrats: [],
    tarifsdetails: [],
    pays: [],
    paysZone: [],
    firstCompId: [],
    tarifs: [],
    tarifsVoyageProd: [],
    garanties: [],
    sousgaranties: [],
    garantierisques: [],
    categories: [],
    branches: [],
    risques: [],
    energies: [],
    compagnies: [],
    qualites: [],
    offres: [],
    offresVoyage: [],
    offressante: [],
    offredetails: [],
    marques: [],
    systemesecurites: [],
    modeles: [],
    usages: [],
    zonecouverturesante: [],
    // ***
    typevehicules: [],
    genrevehicules: [],
    professions: [],
    professionsia: [],
    typesouscripteurs: [],
    typeassures: [],
    categoriepermis: [],
    qualitesouscripteur: [],
    colleges: [],
    isError: false,
    isSuccess: false,
    isLoading: false,
    message: ''
}

// create new contrat
export const createContrat = createAsyncThunk('contrats/create', async (contratData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.user.token
        return await contratService.createContrat(contratData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// get user contract
export const getContrats = createAsyncThunk('contrats/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.user.token
        return await contratService.getContrats(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
 })

// getTARIFS DETAILS
export const getTarifsdetails = createAsyncThunk('tarifsdetails/getAll', async(_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTarifsdetails(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// TARIFS
export const getTarifs = createAsyncThunk('tarifs/getAll', async (idproduit, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTarifs(idproduit, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// TARIFS
export const getTarifsVoyage = createAsyncThunk('tarifsvoyage/getAll', async (idproduit, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTarifs(idproduit, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GARANTIES
export const getGaranties = createAsyncThunk('garanties/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getGaranties(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// SOUS GARANTIES
export const getSousgaranties = createAsyncThunk('sousgaranties/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getSousgaranties(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GARANTIES RISQUES
export const getGarantierisques = createAsyncThunk('garantierisques/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getGarantierisques(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// CATEGORIES
export const getCategories = createAsyncThunk('categories/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getCategories(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// BRANCHES
export const getBranches = createAsyncThunk('branches/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getBranches(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// RISQUES
export const getRisques = createAsyncThunk('risques/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getRisques(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// ENERGIES
export const getEnergies = createAsyncThunk('energies/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getEnergies(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// COMPAGNIES
export const getCompagnies = createAsyncThunk('compagnies/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getCompagnies(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// QUALITES
export const getQualites = createAsyncThunk('qualites/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getQualites(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// OFFRES
export const getOffres = createAsyncThunk(
    'offres/getAll',
    async ({ idproduit, idtarif }, thunkAPI) => {
        try {
            const token = thunkAPI.getState().auth.token;
            return await contratService.getOffres({ idproduit, idtarif, token });
        } catch (error) {
            const message = error.response?.data ? Object.values(error.response.data).flat()[0] : 'An error occurred';
            return thunkAPI.rejectWithValue(message);
        }
    }
);
// OFFRES VOYAGES
export const getOffresVoyages = createAsyncThunk('offresvoyage/getAll', async (idproduit, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getOffresVoyages(idproduit, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})


// OFFRES SANTE
export const getOffresSante = createAsyncThunk('offressante/getAll', async (idtarif, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getOffresSante(idtarif, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})




// OFFRES DETAILS 
export const getOffredetails = createAsyncThunk('offredetails/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getOffredetails(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// MARQUES 
export const getMarques = createAsyncThunk('marques/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getMarques(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// SYSTEMES SECURITES 
export const getSystemesecurites = createAsyncThunk('systemesecurites/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getSystemesecurites(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// MODELES 
export const getModeles = createAsyncThunk('modeles/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getModeles(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// USAGES 
export const getUsages = createAsyncThunk('usages/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        
        return await contratService.getUsages(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// *** 

// TYPE VEHIULES  
export const getTypeVehicule = createAsyncThunk('typevehicule/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTypeVehicule(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GENRE VEHICULE   
export const getGenreVehicule = createAsyncThunk('genrevehicule/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getGenreVehicule(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

 
// export const getCarteBrume = createAsyncThunk('getCarteBrume/getAll', async (id, thunkAPI) => {
//     try {
//         const token = thunkAPI.getState().auth.token

//         return await contratService.getCarteBrume(token,id)
//     } catch (error) {
//         for (let value of Object.values(error.response.data)) {
//             return thunkAPI.rejectWithValue(value[0])
//         }
//     }
// })



// PROFESSION
export const getProfession = createAsyncThunk('profession/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getProfession(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// PROFESSION IA 
export const getProfessionIA = createAsyncThunk('professionia/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getProfessionIA(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

//   TYPE SOUSCRIPTEUR 
export const getTypeSouscripteur = createAsyncThunk('typesouscripteur/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTypeSouscripteur(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

//   TYPE ASSUREUR
export const getTypeAssure = createAsyncThunk('typeassure/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getTypeAssure(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET PAYS LIST 
export const getPays = createAsyncThunk('pays/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getPays(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET PAYS ZONE LIST 
export const getPaysZone = createAsyncThunk('payszone/getAll', async (idComp, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getPaysZone(idComp, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET PAYS LIST 
export const getCategoriePermis = createAsyncThunk('categoriepermis/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getCategoriePermis(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET QUALITES SOUSCRIPTEURS
export const getQualitesSouscripteur = createAsyncThunk('qualitesouscripteur/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token 

        return await contratService.getQualitesSouscripteur(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET COLLEGES
export const getColleges = createAsyncThunk('colleges/getAll', async (idoffre, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getColleges(idoffre, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// GET ZONE COUVERTURE
export const getZoneCouvertureSante = createAsyncThunk('zonecouverturesante/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token

        return await contratService.getZoneCouvertureSante(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})



// contrat slice 
export const contratSlice = createSlice({
    name: 'contrat',
    initialState,
    reducers: {
        reset: (state) => {
            state.isLoading = false
            state.isSuccess = false
            state.isError = false
            state.message = ''
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(createContrat.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(createContrat.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.clients.push(action.payload);
            })
            .addCase(createContrat.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET CONTRATS
            .addCase(getContrats.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(getContrats.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.contrats = action.payload
            })
            .addCase(getContrats.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET TARIFS DETAILS
            .addCase(getTarifsdetails.pending, (state) => {
                    state.isLoading = true;
                    state.tarifsdetails = []
                })
            .addCase(getTarifsdetails.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.tarifsdetails = action.payload
            })
            .addCase(getTarifsdetails.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET TARIFS
            .addCase(getTarifs.pending, (state) => {
                state.isLoading = true;
                state.tarifs = []
            })
            .addCase(getTarifs.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.tarifs = action.payload
            })
            .addCase(getTarifs.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET TARIFSVOYAGE
            .addCase(getTarifsVoyage.pending, (state) => {
                state.isLoading = true;
                state.tarifsVoyageProd = []
            })
            .addCase(getTarifsVoyage.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.tarifsVoyageProd = action.payload
            })
            .addCase(getTarifsVoyage.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET GARANTIES
            .addCase(getGaranties.pending, (state) => {
                state.isLoading = true;
                state.garanties = []
            })
            .addCase(getGaranties.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.garanties = action.payload
            })
            .addCase(getGaranties.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET SOUS GARANTIES
            .addCase(getSousgaranties.pending, (state) => {
                state.isLoading = true;
                state.sousgaranties = []
            })
            .addCase(getSousgaranties.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.sousgaranties = action.payload
            })
            .addCase(getSousgaranties.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET GARANTIES RISQUE
            .addCase(getGarantierisques.pending, (state) => {
                state.isLoading = true;
                state.garantierisques = []
            })
            .addCase(getGarantierisques.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.garantierisques = action.payload
            })
            .addCase(getGarantierisques.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET CATEGORIES
            .addCase(getCategories.pending, (state) => {
                state.isLoading = true;
                state.categories = []
            })
            .addCase(getCategories.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.categories = action.payload
            })
            .addCase(getCategories.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET BRANCHES
            .addCase(getBranches.pending, (state) => {
                state.isLoading = true;
                state.branches = []
            })
            .addCase(getBranches.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.branches = action.payload
            })
            .addCase(getBranches.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET RISQUES
            .addCase(getRisques.pending, (state) => {
                state.isLoading = true;
                state.risques = []
            })
            .addCase(getRisques.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.risques = action.payload
            })
            .addCase(getRisques.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET ENERGIES
            .addCase(getEnergies.pending, (state) => {
                state.isLoading = true;
                state.energies = []
            })
            .addCase(getEnergies.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.energies = action.payload
            })
            .addCase(getEnergies.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // GET CATEGORIE PERMIS
            .addCase(getCategoriePermis.pending, (state) => {
                state.isLoading = true;
                state.categoriepermis = []
            })
            .addCase(getCategoriePermis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.categoriepermis = action.payload
            })
            .addCase(getCategoriePermis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET COMPAGNIES
            .addCase(getCompagnies.pending, (state) => {
                state.isLoading = true;
                state.compagnies = []
            })
            .addCase(getCompagnies.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.compagnies = action.payload;
                state.firstCompId = action.payload[0]
            })
            .addCase(getCompagnies.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET QUALITES
            .addCase(getQualites.pending, (state) => {
                state.isLoading = true;
                state.qualites = []
            })
            .addCase(getQualites.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.qualites = action.payload
            })
            .addCase(getQualites.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET OFFRES
            .addCase(getOffres.pending, (state) => {
                state.isLoading = true;
                state.offres = []
            })
            .addCase(getOffres.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.offres = action.payload
            })
            .addCase(getOffres.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET OFFRES VOYAGES 
            .addCase(getOffresVoyages.pending, (state) => {
                state.isLoading = true;
                state.offresVoyage = []
            })
            .addCase(getOffresVoyages.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.offresVoyage = action.payload
            })
            .addCase(getOffresVoyages.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // OFFRES SANTE 
            .addCase(getOffresSante.pending, (state) => {
                state.isLoading = true;
                state.offressante = []
            })
            .addCase(getOffresSante.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.offressante = action.payload
            })
            .addCase(getOffresSante.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET OFFREDETAILS
            .addCase(getOffredetails.pending, (state) => {
                state.isLoading = true;
                state.offredetails = []
            })
            .addCase(getOffredetails.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.offredetails = action.payload
            })
            .addCase(getOffredetails.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET MARQUES
            .addCase(getMarques.pending, (state) => {
                state.isLoading = true;
                state.marques = []
            })
            .addCase(getMarques.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.marques = action.payload
            })
            .addCase(getMarques.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET SYSTEMES SECURITES
            .addCase(getSystemesecurites.pending, (state) => {
                state.isLoading = true;
                state.systemesecurites = []
            })
            .addCase(getSystemesecurites.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.systemesecurites = action.payload
            })
            .addCase(getSystemesecurites.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET MODELES
            .addCase(getModeles.pending, (state) => {
                state.isLoading = true;
                state.modeles = []
            })
            .addCase(getModeles.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.modeles = action.payload
            })
            .addCase(getModeles.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GET USAGES
            .addCase(getUsages.pending, (state) => {
                state.isLoading = true;
                state.usages = []
            })
            .addCase(getUsages.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.usages = action.payload
            })
            .addCase(getUsages.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // TYPE VEHICULE 
            .addCase(getTypeVehicule.pending, (state) => {
                state.isLoading = true;
                state.typevehicules = []
            })
            .addCase(getTypeVehicule.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.typevehicules = action.payload
            })
            .addCase(getTypeVehicule.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // GENRE VEHICULE
            .addCase(getGenreVehicule.pending, (state) => {
                state.isLoading = true;
                state.genrevehicules = []
            })
            .addCase(getGenreVehicule.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.genrevehicules = action.payload
            })
            .addCase(getGenreVehicule.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // PROFESSION
            .addCase(getProfession.pending, (state) => {
                state.isLoading = true;
                state.professions = []
            })
            .addCase(getProfession.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.professions = action.payload
            })
            .addCase(getProfession.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // PROFESSION IA
            .addCase(getProfessionIA.pending, (state) => {
                state.isLoading = true;
                state.professionsia = []
            })
            .addCase(getProfessionIA.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.professionsia = action.payload
            })
            .addCase(getProfessionIA.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // TYPE SOUSCRIPTEUR  
            .addCase(getTypeSouscripteur.pending, (state) => {
                state.isLoading = true;
                state.typesouscripteurs = []
            })
            .addCase(getTypeSouscripteur.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.typesouscripteurs = action.payload
            })
            .addCase(getTypeSouscripteur.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // TYPE ASSURE
            .addCase(getTypeAssure.pending, (state) => {
                state.isLoading = true;
                state.typeassures = []
            })
            .addCase(getTypeAssure.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.typeassures = Array.isArray(action.payload) ? action.payload : []
            })
            .addCase(getTypeAssure.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // PAYS
            .addCase(getPays.pending, (state) => {
                state.isLoading = true;
                state.pays = []
            })
            .addCase(getPays.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.pays = action.payload
            })
            .addCase(getPays.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // PAYS
            .addCase(getPaysZone.pending, (state) => {
                state.isLoading = true;
                state.paysZone = []
            })
            .addCase(getPaysZone.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.paysZone = action.payload
            })
            .addCase(getPaysZone.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // QUALITE SOUSCRIPTEUR 
            .addCase(getQualitesSouscripteur.pending, (state) => {
                state.isLoading = true;
                state.qualitesouscripteur = []
            })
            .addCase(getQualitesSouscripteur.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.qualitesouscripteur = action.payload
            })
            .addCase(getQualitesSouscripteur.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // COLLEGES 
            .addCase(getColleges.pending, (state) => {
                state.isLoading = true;
                state.colleges = []
            })
            .addCase(getColleges.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.colleges = action.payload
            })
            .addCase(getColleges.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // ZONE COUVERTURE SANTE
            .addCase(getZoneCouvertureSante.pending, (state) => {
                state.isLoading = true;
                state.zonecouverturesante = []
            })
            .addCase(getZoneCouvertureSante.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.zonecouverturesante = action.payload
            })
            .addCase(getZoneCouvertureSante.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
    }
})

export const { reset } = contratSlice.actions
export default contratSlice.reducer 