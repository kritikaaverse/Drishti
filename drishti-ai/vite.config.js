import {defineConfig} from 'vite';
export default defineConfig({server:{host:'0.0.0.0',allowedHosts:true,proxy:{'/camera-sender':{target:process.env.VITE_API_BASE_URL || 'http://localhost:8000',changeOrigin:true},'/api':{target:process.env.VITE_API_BASE_URL || 'http://localhost:8000',changeOrigin:true,ws:true}}}});
