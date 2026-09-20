import {
    createSlice,
    createAsyncThunk
} from '@reduxjs/toolkit'
import devisService from './devisService';
import Swal from 'sweetalert2'

const initialState = {
    deleteDevis: [],
    deleteAdherent: [],
    deleteAffilie: [],
    validDevis: [],
    savedDevis: [],
    devis: [],
    oneDevis: [],
    savedDevisIa: [],
    savedDevisVoyage: [],
    savedDevisMrh: [],
    savedDevisSante: [],
    savedDevisDommages: [],
    devisinfos: [],
    devisCounts: { nb_devis: 0, nb_contrats: 0 },
    finalisationdevisauto: [],
    devisVoyageSaved: null,
    devisMrhSaved: null,
    devisSanteSaved: null,
    devisIaSaved: null,
    devisDommagesSaved: null,
    devisSaved: null,
    devisValid: null,
    endeddevis: null,
    isError: false,
    isSuccess: false,
    isLoading: false,
    message: ''
}

// save new devis
export const saveDevis = createAsyncThunk('savedevis/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevis(devisData, token)
    } catch (error) {
        if (error.response.data[0].OutputMessage) {
            return thunkAPI.rejectWithValue(error.response.data[0].OutputMessage)
        }
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// ending new devis flotte
export const finalisationdevisauto = createAsyncThunk('finalisationdevisauto/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.finalisationdevisauto(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// saveDevisIA
export const saveDevisIA = createAsyncThunk('savedevisia/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevisIA(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// saveDevisVoyage
export const saveDevisVoyage = createAsyncThunk('savedevisvoyage/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevisVoyage(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// saveDevisSanté
export const saveDevisSante = createAsyncThunk('saveDevisSante/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevisSante(devisData, token)
    } catch (error) {
        const errorReturned = error.response.data
        return thunkAPI.rejectWithValue(errorReturned[0].OutputMessage)
    }
})

//DeleteDevis

// Fonction de redirection sur la page précedente
const handleGoBack = (navigate) => {
    navigate(-1);
};

export const confirmDeletedDevis = (id, dispatch, navigate) => {
    Swal.fire({
        title: "Attention !!",
        text: "Archivage en cours, désirez-vous poursuivre cette action ?",
        icon: "error",
        showCancelButton: true,
        showCloseButton: true,
        confirmButtonText: "Oui, Archiver",
        cancelButtonText: "Non, retour",
        reverseButtons: true,
    }).then((result) => {
        if (result.isConfirmed) {
            const devisData = {
                IdDevis: id
            }
            dispatch(deleteDevis(devisData))
            Swal.fire('Devis Archivé avec succès !!', '', 'success')
            handleGoBack(navigate);
        } else if (result.dismiss === Swal.DismissReason.cancel) { }
    });
}

const deleteDevis = createAsyncThunk('deleteDevis/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.deleteDevisService(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

export const confirmDeletedAdherent = (idAdherent, idDevis, dispatch, setGroupAdherentIndex) => {
    Swal.fire({
        title: "Attention !!",
        text: "Suppression en cours, désirez-vous poursuivre cette action ?",
        icon: "error",
        showCancelButton: true,
        showCloseButton: true,
        confirmButtonText: "Oui, supprimer",
        cancelButtonText: "Non, retour",
        reverseButtons: true,
    }).then(async (result) => {
        if (result.isConfirmed) {
            const adherentData = {
                id_devis: idDevis,
                id_objet: idAdherent
            }
            await dispatch(deleteAdherent(adherentData))
            Swal.fire('Adhérent supprimé avec succès !!', '', 'success')
        } else if (result.dismiss === Swal.DismissReason.cancel) { }
        setGroupAdherentIndex(new Date())
    });
}




export const confirmDeletedAffilie = (idAffilie, idDevis, dispatch, setGroupAffilieIndex) => {
    Swal.fire({
        title: "Attention !!",
        text: "Suppression en cours, désirez-vous poursuivre cette action ?",
        icon: "error",
        showCancelButton: true,
        showCloseButton: true,
        confirmButtonText: "Oui, supprimer",
        cancelButtonText: "Non, retour",
        reverseButtons: true,
    }).then(async (result) => {
        if (result.isConfirmed) {
            const affilieData = {
                id_devis: idDevis,
                id_objet: idAffilie
            }
            await dispatch(deleteAffilie(affilieData))
            Swal.fire('Affilié supprimé avec succès !!', '', 'success')
        } else if (result.dismiss === Swal.DismissReason.cancel) { }
        setGroupAffilieIndex(new Date())
    });
}

// suppression d'un Adhérent dans la liste des Adhérents 
export const deleteAdherent = createAsyncThunk('deleteAdherent/create', async (adherentData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.deleteAdherentService(adherentData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})


// suppression d'un Adhérent dans la liste des Adhérents 
export const deleteAffilie = createAsyncThunk('deleteAffilie/create', async (adherentData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.deleteAffilieService(adherentData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})


// saveDevisMrh
export const saveDevisMrh = createAsyncThunk('savedevismrh/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevisMrh(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// saveDevisMrh
export const saveDevisDommages = createAsyncThunk('savedevisdommages/create', async (devisData, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.saveDevisDommages(devisData, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// get saved devis 
export const getSavedDevis = createAsyncThunk('saveddevis/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getSavedDevis(token)

    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// validate newDevis
export const validateDevis = createAsyncThunk('validatedevis/create', async (validationDetail, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.validateDevis(validationDetail, token)
    } catch (error) {
        const data = error.response?.data;
        // Gérer le format [{ObjectId: 0, OutputMessage: "..."}]
        if (Array.isArray(data) && data[0]?.OutputMessage) {
            return thunkAPI.rejectWithValue(data[0].OutputMessage);
        }
        // Fallback pour les autres formats d'erreur
        for (let value of Object.values(data || {})) {
            if (typeof value === 'string') return thunkAPI.rejectWithValue(value);
            if (Array.isArray(value) && value[0]) return thunkAPI.rejectWithValue(value[0]);
        }
        return thunkAPI.rejectWithValue("Une erreur est survenue lors de la validation");
    }
})

// get valid devis
export const getValidDevis = createAsyncThunk('validdevis/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getValidDevis(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// get valid devis
export const getDevis = createAsyncThunk('devis/getAll', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getDevis(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})



// get One Devis
export const getOneDevis = createAsyncThunk('devis/getOne', async (_, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getOneDevis(token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})

// get Devis counts
export const getDevisCounts = createAsyncThunk('devisinfo/getCounts', async (id, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getDevisCounts(id, token)
    } catch (error) {
        return thunkAPI.rejectWithValue(error?.response?.data?.data ?? error.message)
    }
})

// get Devis Infos
export const getDevisInfo = createAsyncThunk('devisinfo/getAll', async (id, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.getDevisInfo(id, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})



export const annulationDevis = createAsyncThunk('annulationdevis/create', async (annulationDetail, thunkAPI) => {
    try {
        const token = thunkAPI.getState().auth.token
        return await devisService.annulationDevis(annulationDetail, token)
    } catch (error) {
        for (let value of Object.values(error.response.data)) {
            return thunkAPI.rejectWithValue(value[0])
        }
    }
})




export const devisSlice = createSlice({
    name: 'devis',
    initialState,
    reducers: {
        reset: (state) => {
            state.isLoading = false
            state.devisSaved = null
            state.devisValid = null
            state.oneDevis = []
            state.isSuccess = false
            state.isError = false
            state.message = ''
        }
    },
    extraReducers: (builder) => {
        builder
            //annulation devis
            .addCase(annulationDevis.pending, (state) => {
                state.isLoading = true
            })
            .addCase(annulationDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.devisVoyageSaved = action.payload[0]
            })
            // get devis infos 
            .addCase(getDevisInfo.pending, (state) => {
                state.isLoading = true
            })
            .addCase(getDevisInfo.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.devisinfos = action.payload?.data ?? action.payload ?? []
            })
            .addCase(getDevisInfo.rejected, (state, action) => {
                state.isError = true
                state.isLoading = false
                state.message = action.payload
            })
            // get devis counts
            .addCase(getDevisCounts.fulfilled, (state, action) => {
                state.devisCounts = action.payload?.data ?? state.devisCounts
            })
            // save devis
            .addCase(saveDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevis.push(action.payload)
                state.devisSaved = action.payload[0]
            })
            .addCase(saveDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // ending devis auto
            .addCase(finalisationdevisauto.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(finalisationdevisauto.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.finalisationdevisauto.push(action.payload)
                state.endeddevis = action.payload[0]
            })
            .addCase(finalisationdevisauto.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // save devis IA
            .addCase(saveDevisIA.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevisIA.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevisIa.push(action.payload)
                state.devisIaSaved = action.payload[0]
            })
            .addCase(saveDevisIA.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // save devis MRH
            .addCase(saveDevisMrh.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevisMrh.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevisMrh.push(action.payload)
                state.devisMrhSaved = action.payload[0]
            })
            .addCase(saveDevisMrh.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // save devis DOMMAGES
            .addCase(saveDevisDommages.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevisDommages.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevisDommages.push(action.payload)
                state.devisDommagesSaved = action.payload[0]
            })
            .addCase(saveDevisDommages.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // save devis VOYAGE
            .addCase(saveDevisVoyage.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevisVoyage.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevisVoyage.push(action.payload)
                state.devisVoyageSaved = action.payload[0]
            })
            .addCase(saveDevisVoyage.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // save devis SANTE
            .addCase(saveDevisSante.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(saveDevisSante.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.savedDevisSante.push(action.payload)
                state.devisSanteSaved = action.payload[0]
            })
            .addCase(saveDevisSante.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            // validateDevis
            .addCase(validateDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(validateDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.validDevis.push(action.payload)
                state.devisValid = action.payload[0]
            })
            .addCase(validateDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            //DeleteDevis
            .addCase(deleteDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(deleteDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.deleteDevis.push(action.payload)
            })
            .addCase(deleteDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })

            //DeleteAdherent
            .addCase(deleteAdherent.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(deleteAdherent.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.deleteAdherent.push(action.payload)
            })
            .addCase(deleteAdherent.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })


            // get saved devis
            .addCase(getSavedDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(getSavedDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.devis = action.payload
            })
            .addCase(getSavedDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // get valid devis 
            .addCase(getValidDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(getValidDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.validDevis = action.payload
            })
            .addCase(getValidDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // get devis 
            .addCase(getDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(getDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.devis = action.payload
            })
            .addCase(getDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
            // get onedevis 
            .addCase(getOneDevis.pending, (state) => {
                state.isLoading = true;
            })
            .addCase(getOneDevis.fulfilled, (state, action) => {
                state.isLoading = false;
                state.isSuccess = true;
                state.oneDevis = action.payload
            })
            .addCase(getOneDevis.rejected, (state, action) => {
                state.isLoading = false;
                state.isError = true;
                state.message = action.payload;
            })
    }
})

export const {
    reset
} = devisSlice.actions
export default devisSlice.reducer