import {useEffect,useState} from 'react';
import {connectRealtime,DEMO_MODE} from '../services/api';
export default function useRealtime(onMessage,onError){const[keyVersion,setKeyVersion]=useState(0);useEffect(()=>{const changed=()=>setKeyVersion(v=>v+1);window.addEventListener('drishti-key-changed',changed);return()=>window.removeEventListener('drishti-key-changed',changed)},[]);useEffect(()=>{if(DEMO_MODE)return;const ws=connectRealtime(onMessage,onError);return()=>ws.close()},[onMessage,onError,keyVersion])}
