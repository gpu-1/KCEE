import {defineConfig} from 'vite';
const proxy={'/api':{target:process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',changeOrigin:true,rewrite:path=>path.replace(/^\/api/,'')}};
export default defineConfig({server:{host:'0.0.0.0',port:5173,strictPort:true,allowedHosts:['viewer'],proxy},preview:{host:'0.0.0.0',port:5173,strictPort:true,allowedHosts:['viewer'],proxy}});
