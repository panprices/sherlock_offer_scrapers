# Idealo Observation Log

1. [March 10, 2020. String search and EAN search on the website.](#string-search-and-ean-search-through-the-website)
2. [October 5, 2020. GTIN and attempts to bypass the Capcha.](#gtin-and-attempts-to-bypass-the-capcha)
3. [December 11, 2020. Attacking the Mobile App.](#attacking-the-mobile-app)
4. [December 21, 2020. Captcha on product pages due to IP address](#captcha-on-product-pages-due-to-ip-address)
5. [December 28, 2020. Dynamic rendering of Product Name](#dynamic-rendering-of-product-name)
6. [December 16, 2021. Rate limit with Http status code 429](#rate-limit-with-http-status-code-429)
7. [January 03, 2022. Rate limited for 4 days then back to normal](#rate-limited-for-4-days-then-back-to-normal)

---

### String search and EAN search through the website
###### March 10, 2020

Google IP range seems to be fried, at least EUW-3 where Captcha is served at least 50% of the times on those IPs.

Searching with strings seems to work pretty good (Geolocation set to DE, UK worked badly).
Especially with scraperAPI where we had 95 out of 95 successful product querys without using their JS-rendering and residential IP functions.

#### Search with EAN

Searching with EAN seems to be diffcult since they almost always throw Captcha on the first request from an new IP. If you solve it, you always seem to be allowed at least 6 more EAN queries before next Captcha.

With scraperAPI, with residential IP and JS rendering, captcha HTML was returned relatively fast (maybe 20s). With only JS-rendering, they usually returned the HTML but it took longer (maybe 40s). Without JS-rendering and residential IP, the proxy usually did not respond and timeout eventually.


---
### GTIN and attempts to bypass the Capcha
###### October 5, 2020

Their behavior is the same
- Search with string: no CAPTCHA encountered
- Search with GTIN (EAN): they throw out CAPTCHA, you are a human or a bot doesn't matter, CAPTCHA, CAPTCHA, CAPTCHA. After solving the CAPTCHA, the current IP is whitelisted for about 6 more requests before you meet CAPTCHA again.
#### Attempt to bypass their protection
Because they are really serious about searching with GTIN, so either you find a way to bypass CAPTCHA, or find alternative sources.
Things I have tried:
- Programmatically click the checkbox: Not working. Even when you do that in Puppeteer with Stealth plugin, passing every bot testing, even look like human more than the human itself, somehow Google still know, you are a bot.
- Intercept response: Not working. When you click the checkbox, a POST request is sent, and its reponse determine you are a bot or not. I tried to intercept and change the response data, if I changed 2 keys, then I wouldn't pass, if I replace the entier body with the valid body state that I'm passed, the puppeteer hang/freeze. Not sure this is a puppeteer bug or the captcha.

I can try to intercept the request and change the data sent to Google server, but I pretty sure that this won't work, and it is hard, too. They send a lot of base64 encoded of binary data, in a lot of place: post body, query params, headers, maybe cookies.

#### Using a Captcha solving service
This definitely work, but the response time is the problem. One service we can try is 2captcha, with 3USD for solving reCAPTCHA 1000 times, with the response time around 15-20s. For live search this is too long. However, because everytime we solve a Captcha, we can send 6 more requests, so total 7 requests for 1 solve in 15-20s. We could workaround this by implementing IP rotation by ourselves. It's work as follow:
- Keep a list of how many requests left could be made on an IP before we receive captcha again
- If an IP run out of free request, the system (cloud pubsub, function,...) trigger a search on that IP automatically, without user request, to solve the captcha and whitelist that IP again.
- Distribute the request among IPs with has free requests.

We have 6 free requests for each IP (1 request for solving captcha), for each search we have at least 3 variants (each product have 1 variant, which is itself) up to over 150 variants (like [this one](https://www.google.com/shopping/product/11730474391855567935)), the average number of variant is 3 per product, so one search generate 9 GTIN on average, which will consume 1,5 IP resources. Right now we have 50 IP, which can receive 50 * 6 = 300 requests per 20s (time to solve captcha) or 300/9 = 33.333 search times per 20s, which I think we need a very high load to reach that amount of search that short amount of time interval.

And 1000/50 = 20, it means we can whitelist the entire IP list 20 times for 3USD, or 3 USD for 33.333 * 20 = 666.666 search times, or 6000 requests.

---
### Attacking the Mobile App
###### December 11, 2020

Since the [idealo.de](https://www.idealo.de/) website has a very aggressive captcha protection, we turned to their mobile app as an alternative.

Initally searching with GTIN on the mobile app seems to work fine with no captcha, so we thought they might use a different way to get the data compared to their website, namely an API endpoint. After a while we noticed that there are still captchas, though we continued since we would still like to have an API endpoint to potentially stress test it.

#### Capture Mobile Traffic
Since there are no tools like Google Chrome Developer Tool come pre-installed on a mobile device, we needed to find a way to access network traffic data. Here is a summary of tried approaches.

##### Approach 1. Capture network traffic of the mobile phone with Android Studio's profiler tool

Profiler tool: https://developer.android.com/studio/profile/network-profiler

**Problem.** Network can only be captured with apps in "debug" mode, not "release". In orther words, the tool is set up so that only developer of their own app can monitor the traffic, and we cannot monitor network traffic of apps released on Playstore with this tool.


##### Approach 2. Create an android emulator, then use `tcpdump` to capture network traffic.

See [this answer on stackoverlow](https://stackoverflow.com/a/2574493) for the details. The acquired data, however, is a log of the Transport network layer TCP and not the higher level Application network layer HTTP. I am not sure if we can interpret the HTTP packages from that, or at the very least I wasn't be able to (Toan).

##### Approach 3. Create an android emulator, then use [mitm](https://mitmproxy.org/) as a proxy to capture http network traffic.

See [this](https://towardsdatascience.com/data-scraping-android-apps-b15b93aa23aa) for the tutorial on setting up the `mitm` proxy to capture http requests.

**Problem.**  Using the idealo app with the proxy results in a connection error, which the idealo app notify the user with "A network error occured, please try again".

This is likely to be a problem due to the Android 7 update: ["Apps that target API Level 24 and above no longer trust user or admin-added CAs for secure connections, by default."](https://android-developers.googleblog.com/2016/07/changes-to-trusted-certificate.html). Since applications do not trust user-added CA anymore, the added certificate of `mitm` did not work.

##### Approach 4. Use [Fiddler](https://www.telerik.com/fiddler) and set the PC as a proxy to capture the phone's http traffic.

If the PC and the mobile device is connected to the same network, we can connect the phone to the PC and let the PC be a proxy using Fiddler. Then we can use Fiddler to capture the phone's http traffic.

**Problem.** Cannot capture https requests, only http. There's an option to add Fiddler's certificate to our PC for capturing https but that doesn't work either.

##### Approach 5. Use an app from the Android device itself.

**Problem.** All the apps that does not require the device to be rooted cannot capture https requests.

Then the only option left is to use apps that require root. Rooting an emulated device is not that straight forward, and due to time limitation & small success rate, we stopped here.


#### Conclusions concerning the Mobile App
- Unless we root the mobile device so that we can add the proxy's certificate as a system certificate instead of an user one, proxies will not work on https requests.
- There are network errors with the native app on my mobile phone even without using any proxies or vpn. It only happen when connecting to SSE Business Lab A house's wifi and does not happen on 4G or other wifi. This probably mean they have blacklisted us.

---
### Captcha on product pages due to IP address
###### December 21, 2020
By using PriceAPI we can now cache product urls of our most popular products. 
However, making a request directly to a product page such as https://www.idealo.de/preisvergleich/OffersOfProduct/5122178 on Google Cloud still results in the Captcha problem. It does not happen when making request locally at SSE business lab however.

Our guess is that Idealo blacklisted the IP address of Google Cloud datacenters.
Therefore, the first solution comes to mind is to overcome with a proxy. Among the three datacenter proxies from SE, UK, DE on Oxylabs.io that we have, only the UK one works. Our guess is that the datacenter in the UK is a small one which Idealo missed while the other two are known to them.

Thus, we are currently using the UK proxy for now. If they happen to block that one in the future, we might need to get a residential proxy instead.


### Dynamic rendering of Product Name
###### December 28, 2020
Sometimes the Idealo websites (especially those other than the DE sites) renders the product name dynamically like this:
```html
<span class="productOffers-listItemTitleInner one-line-limit"
						  id="result-3-offerinfo">
							<script type="text/javascript">
							document.getElementById("result-3-offerinfo").title = document.getElementById("result-3-offerinfo").innerHTML = idealoApp.getContents('!2?2D@?:4 {F>:I s|r\\{)`d q=24< cz q=24< {)\\`d');
							</script>
							</span>
				</a>
```
where the `idealoApp.getContents()` function is just a ROT47 decoder (a very simple shift cipher). 
The reason why they do this is unknown but it makes our parsing function a tiny bit more complicated.

---
## Rate limit with Http status code 429
###### December 16, 2021

### Background
We have been encountering status code 429 from the summer (around June/July?). Then last October we started to get 429 on all of our requests.

We tried to change the request-headers, mainly on User-Agent, and it worked, but only for a few hours. Thus we suspected that Idealo block us based on a combination of (IP, User-Agent) or (IP-range, User-Agent). 

### Current solution
We now have randomly rotate between a list of ~120 User-Agent and 50 Oxylabs' ISK German IPs. 

We experimented with making 60 requests in 30 minutes with only 1 IP using rotating User-Agent, and did not get blocked. 


---
## Rate limited for 4 days then back to normal
###### January 03, 2022

From 20:00 December 28th to 19:00 January 1st, we got rate limited (http status code 429 + captcha) for 60-70% of our requests. We got 0 offers so 60-70% probably means that the other remaining 30-40% requests returned empty (404) pages or where broken for some other reason. And that *all* (100%) valid requests got rate limited.

This was due to us enabling the domain-fetcher on 15:00 December 28th, after a long time having it disabled. And since there a lot of pub/sub messages in the queue, we spammed idealo with a rate of approximately 6000 requests/hour distributed over 50 static residential DE proxies. We however quickly realised this and turned it off after 45 minutes.

We quickly turned off the domain-fetcher module, but 4 hours later we got 429 from Idealo. It's strange that (1) it takes so long for Idealo to start blocking us, and (2) our Swedish data center proxy was blocked for almost a year, but this time our proxies are only blocked for 4 days. Point (2) can be think of as an evidence showing that idealo block us not solely by IPs but by other identification as well, such as User-Agent.
