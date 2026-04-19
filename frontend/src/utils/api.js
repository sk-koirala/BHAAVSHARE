import axios from 'axios';

export const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
});

// Attach JWT from localStorage automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bhaav_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-logout on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      const path = window.location.pathname;
      if (path !== '/login' && path !== '/signup') {
        localStorage.removeItem('bhaav_token');
        localStorage.removeItem('bhaav_user');
      }
    }
    return Promise.reject(err);
  }
);

export default api;

// Canonical NEPSE universe for client-side pickers
export const ALL_STOCKS = [
  "ADBL","AHPC","AKJCL","AKPL","ALICL","API","BARUN","BFC","BOKL","BPCL",
  "CBL","CCBL","CFCL","CGH","CHCL","CHDC","CHL","CIT","CORBL","CZBIL",
  "DHPL","EBL","EDBL","GBBL","GBIME","GFCL","GHL","GLH","GLICL","GMFIL",
  "GRDBL","GUFL","HBL","HDHPC","HIDCL","HPPL","HURJA","ICFC","JBBL","JFL",
  "JLI","JOSHI","KBL","KKHC","KPCL","KRBL","KSBBL","LBBL","LBL","LEC",
  "LICN","MBL","MDB","MEGA","MEN","MFIL","MHNL","MKJC","MLBL","MNBBL",
  "MPFL","NABBC","NABIL","NBB","NBL","NCCB","NFS","NGPL","NHDL","NHPC",
  "NIB","NICA","NIFRA","NLIC","NLICL","NMB","NRN","NYADI","OHL","PCBL",
  "PFL","PLI","PLIC","PMHPL","PPCL","PROFL","PRVU","RADHI","RHPC","RHPL",
  "RLFL","RLI","RRHP","RURU","SADBL","SAHAS","SANIMA","SAPDBL","SBI","SBL",
  "SCB","SFCL","SHBL","SHEL","SHINE","SHL","SHPC","SIFC","SINDU","SJCL",
  "SLI","SLICL","SPC","SPDL","SRBL","SSHL","TPC","TRH","ULI","UMHL",
  "UMRH","UNHPL","UPCL","UPPER"
];
