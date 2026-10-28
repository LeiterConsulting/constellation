/// <reference types="vite/client" />

declare module 'crypto-js/sha256' { const sha256: (value: string) => { toString(): string }; export default sha256; }
