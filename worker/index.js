// Receiptly secure AI receipt scanner backend (Cloudflare Worker).
// Secrets are configured in Cloudflare, never stored in GitHub or the APK.
// Every public AI request requires a valid single-use Turnstile token.
const ORIGIN = "https://apandya-app.github.io";
const categories = ["Groceries","Restaurants","Transport","Shopping","Entertainment","Healthcare","Other"];
function response(body, status=200, origin=ORIGIN) {
  return new Response(JSON.stringify(body), {
    status, headers: {"Content-Type":"application/json; charset=utf-8",
      "Access-Control-Allow-Origin":origin, "Vary":"Origin", "Cache-Control":"no-store",
      "Access-Control-Allow-Methods":"POST, OPTIONS",
      "Access-Control-Allow-Headers":"Content-Type"}
  });
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin");
    if (origin !== ORIGIN) return response({error:"Origin not allowed."},403);
    const path = new URL(request.url).pathname;
    if (path !== "/scan") return response({error:"Not found."},404);
    if (request.method === "OPTIONS") return response({},204);
    if (request.method !== "POST") return response({error:"POST required."},405);
    if (!env.OPENAI_API_KEY || !env.TURNSTILE_SECRET_KEY || !env.RECEIPT_RATE_LIMIT)
      return response({error:"AI scanner backend is not configured."},503);
    if (!String(request.headers.get("Content-Type")||"").startsWith("application/json"))
      return response({error:"Expected JSON."},415);
    const len=Number(request.headers.get("Content-Length")||0);
    if (len > 7500000) return response({error:"Image too large."},413);
    let payload;
    try { payload=await request.json(); } catch { return response({error:"Invalid JSON."},400); }
    const image=payload && payload.image;
    const turnstileToken=payload && payload.turnstileToken;
    if (typeof image!=="string" || image.length>7200000 ||
        !/^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(image))
      return response({error:"Please upload a valid JPG, PNG or WebP receipt under 5 MB."},400);
    if (typeof turnstileToken!=="string" || turnstileToken.length<10 || turnstileToken.length>2048)
      return response({error:"Complete the security verification to use AI."},403);
    let verification;
    try {
      const verified=await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY,response:turnstileToken,
          remoteip:request.headers.get("CF-Connecting-IP")||undefined})
      });
      verification=await verified.json();
    } catch {return response({error:"Security verification is unavailable."},503);}
    if (!verification.success || verification.hostname!=="apandya-app.github.io")
      return response({error:"Security verification failed. Please retry."},403);
    // This rate limit is approximate and per Cloudflare location; set API spending limits too.
    const ip=request.headers.get("CF-Connecting-IP")||"unknown";
    const limited=await env.RECEIPT_RATE_LIMIT.limit({key:ip});
    if (!limited.success) return response({error:"Too many scans. Please retry later."},429);
    const instruction=[
      "Extract the receipt's merchant, final amount actually paid, date, purchased item names, currency and one category.",
      "Read the business name at the TOP, including multiple-line headings; ignore addresses, receipt labels and phone numbers.",
      "Use total paid after discounts, not subtotal, VAT, balance or cash tendered.",
      "If any field is unreadable, return an empty value; never invent data.",
      "Date must be YYYY-MM-DD if visible and unambiguous, otherwise empty.",
      "Category must be one of: "+categories.join(", ")+". Infer using shop AND actual items; if unclear choose Other.",
      "Amount is a number, without currency symbols; if not confident use null.",
      "For all money values preserve the original currency; do not convert to GBP.",
      "Reply ONLY as a JSON object with keys merchant, amount, date, category, currency, items, notes.",
      "items is a list of up to 30 short product names. notes is a list of short warnings."
    ].join(" ");
    let api;
    try {
      const upstream=await fetch("https://api.openai.com/v1/responses",{
        method:"POST",
        headers:{"Authorization":"Bearer "+env.OPENAI_API_KEY,
          "Content-Type":"application/json"},
        body:JSON.stringify({
          model:"gpt-4.1-mini",store:false,max_output_tokens:650,
          input:[{role:"user",content:[
            {type:"input_text",text:instruction},
            {type:"input_image",image_url:image,detail:"high"}
          ]}],
          text:{format:{type:"json_object"}}
        })
      });
      if(!upstream.ok) return response({error:"AI service unavailable ("+upstream.status+")."},502);
      api=await upstream.json();
    }catch{return response({error:"Could not reach the AI service."},502);}
    const raw=(api.output||[]).flatMap(x=>x.content||[])
      .filter(x=>x.type==="output_text").map(x=>x.text||"").join("");
    let result;
    try{result=JSON.parse(raw);}catch{return response({error:"AI returned an unreadable result."},502);}
    const merchant=typeof result.merchant==="string"?result.merchant.trim().slice(0,120):"";
    const amount=(typeof result.amount==="number" && Number.isFinite(result.amount) &&
      result.amount>0 && result.amount<1000000)?Math.round(result.amount*100)/100:null;
    const date=typeof result.date==="string" && /^\d{4}-\d{2}-\d{2}$/.test(result.date)?
      result.date:"";
    const category=categories.includes(result.category)?result.category:"Other";
    const currency=["GBP","USD","EUR"].includes(result.currency)?result.currency:"UNKNOWN";
    const items=Array.isArray(result.items)?result.items.filter(x=>typeof x==="string")
      .slice(0,30).map(x=>x.slice(0,100)):[];
    const notes=Array.isArray(result.notes)?result.notes.filter(x=>typeof x==="string")
      .slice(0,5).map(x=>x.slice(0,180)):[];
    return response({merchant,amount,date,category,currency,items,notes});
  }
};
