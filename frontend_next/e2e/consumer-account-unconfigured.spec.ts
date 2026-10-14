import { expect, test } from "@playwright/test";
import { statSync } from "node:fs";
import path from "node:path";
import { accountCopy } from "../lib/account-copy";

test.skip(process.env.WAVE1A_UNCONFIGURED !== "1", "explicit unconfigured production-build acceptance only");
for (const locale of ["zh-TW", "en", "ja", "ko"] as const) for (const width of [390, 430, 1024, 1440]) {
  test(`${locale} ${width}: unavailable configuration fails closed on all account routes`, async ({page}) => {
    await page.setViewportSize({width,height:900});
    const external:string[]=[];
    await page.route("**/*",route=>{
      const url=new URL(route.request().url());
      if (!['127.0.0.1','localhost'].includes(url.hostname)) { external.push(url.hostname); return route.abort(); }
      return route.continue();
    });
    for(const mode of ["login","signup","account"] as const) {
      await page.goto(`/${mode}`); await page.getByTestId("locale-switcher").selectOption(locale);
      await expect(page.getByRole("heading",{level:1,name:accountCopy[locale][mode]})).toBeVisible();
      await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy[locale].unavailable);
      if(mode!=="account") await expect(page.getByRole("button",{name:accountCopy[locale][mode==="login"?"submitLogin":"submitSignup"],exact:true})).toBeDisabled();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    }
    expect(external).toHaveLength(0);
  });
}
test("measure actual production assets for the three account routes",async({browser},info)=>{
  const result:Record<string,{client_bytes:number;client_files:string[]}>= {};
  for(const route of ["/login","/signup","/account"]) {
    const context=await browser.newContext(); const page=await context.newPage(); const files=new Set<string>();
    // Match Performance Budget v2: cold document/static assets, excluding prefetch.
    await page.route("**/*",r=>{
      const request=r.request(), url=new URL(request.url()), headers=request.headers();
      const allowed=['127.0.0.1','localhost'].includes(url.hostname) && request.method()==='GET'
        && !headers['next-router-prefetch'] && headers.purpose!=='prefetch' && !headers['sec-purpose']?.includes('prefetch')
        && (url.pathname.startsWith('/_next/static/') || request.isNavigationRequest());
      return allowed?r.continue():r.abort();
    });
    page.on("response",response=>{
      const name=new URL(response.url()).pathname;
      if(name.startsWith('/_next/static/') && /\.(?:js|css)$/.test(name)) files.add(name.replace('/_next/',''));
    });
    await page.goto(`${info.project.use.baseURL}${route}`); await expect(page.locator('main [role="alert"]')).toHaveText(accountCopy['zh-TW'].unavailable);
    await page.waitForLoadState('networkidle');
    const client_files=[...files].sort();
    expect(client_files.length).toBeGreaterThan(0);
    result[route]={client_bytes:client_files.reduce((sum,file)=>sum+statSync(path.join(process.cwd(),'.next',file)).size,0),client_files};
    await context.close();
  }
  await info.attach('account-route-assets.json',{body:JSON.stringify(result,null,2),contentType:'application/json'});
  console.log(`ACCOUNT_ROUTE_ASSETS=${JSON.stringify(result)}`);
});
