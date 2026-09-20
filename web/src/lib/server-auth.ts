import { createClient } from "@supabase/supabase-js";
import { NextRequest } from "next/server";
export async function getUserFromRequest(request:NextRequest){
 const header=request.headers.get("authorization"); if(!header?.startsWith("Bearer ")) throw new Error("Missing authorization token");
 const token=header.slice(7);
 const supabase=createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!,process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,{auth:{persistSession:false,autoRefreshToken:false}});
 const {data,error}=await supabase.auth.getUser(token); if(error||!data.user) throw new Error("Invalid authorization token"); return data.user;
}
export function adminSupabase(){ return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!,process.env.SUPABASE_SERVICE_ROLE_KEY!,{auth:{persistSession:false,autoRefreshToken:false}}); }