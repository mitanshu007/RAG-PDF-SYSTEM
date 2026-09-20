import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title:"NEXA — Knowledge Workspace", description:"Private PDF knowledge workspace with retrieval-augmented AI." };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }