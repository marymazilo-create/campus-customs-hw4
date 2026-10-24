# Usability improvements (Problem 9)

Four improvements to the Campus Customs shop: two on the website (front end) and two in Will, the chatbot (agent/backend). Each is built and running in the app.

| # | Improvement | Type | Where to see it |
|---|---|---|---|
| 1 | My size filter | Front end | Products page → "My size" row; size tags on cards; product page starts on your size |
| 2 | Shop for… (who it's for) | Front end | Home page → "Shop for…" tiles; Products page → "Shop for" row |
| 3 | Size-aware search (`find_in_size`) | Agent | Ask Will "got any hoodies in medium?" |
| 4 | Find similar items (`find_similar`) | Agent | Ask Will about a size that's sold out, or a color a product doesn't come in |

---

## 1. My size filter (front end)

**What was added**
- A **"My size"** row on the Products page: Any, XS, S, M, L, XL, XXL.
- Pick a size and the page shows **only products in stock in that size**. The count says so ("21 items in stock in M").
- Every card shows that size's stock: a green **"M: in stock"** or an orange **"M: only 5 left"** tag.
- The size is **remembered** in the browser, so it's still set on the next visit, and works for guests too.
- Open a product and its page **starts with your size selected**, showing how many are left.
- It works together with search, Type and "Shop for" (for example Hoodies + M).
- Code: `frontend/src/mySize.ts`, `pages/Products.tsx`, `components/ProductCard.tsx`, `pages/ProductPage.tsx`; backend `GET /api/products?size=M` in `main.py`.

**Why it helps**
- **Shopper:** no more clicking into product after product only to find their size is gone. With about 145 size slots sold out across the catalogue, that happens a lot. They see only what they can actually buy.
- **Business:** fewer dead ends means fewer abandoned visits. The "only 5 left" tag adds honest urgency on items that are running low.

## 2. Shop for… (front end)

**What was added**
- A **"Shop for…"** section on the Home page with tiles: For Mom, For Dad, For Grandparents, For the Family (Aunt, Uncle, Brother, Cousin), Residential Colleges, Grad & Professional Schools, Athletes & Fans. Each shows a photo, a one-line description and how many styles it has.
- The same groups as a **"Shop for"** row on the Products page (`/products?for=mom`), combinable with Type and My size.
- The groups are defined once in the backend (`tools.py`, `AUDIENCES`) and served by `GET /api/audiences`, so the counts are always right.

**Why it helps**
- **Shopper:** many Campus Customs shoppers aren't buying for themselves. They're parents, grandparents and relatives shopping for a Yale student, or alumni looking for their college or school. Before, finding "something for Grandpa" meant guessing search words. Now it's one tap.
- **Business:** the family lines (Yale Mom, Dad, Grandma, Grandpa, Aunt, Uncle, Brother, Cousin) and the residential college and school lines are gift sellers that were buried among 102 products. Putting them up front drives gift sales, especially around Family Weekend, Commencement and the holidays.

## 3. Size-aware search: `find_in_size` (agent)

**What was added**
- A new agent tool, `find_in_size(size, query, category)`. One call returns only products that match **and are in stock in the shopper's size**, with the quantity and status for that size.
- It understands "medium", "2XL", "small" and so on.
- `prompt.md` tells Will to use it whenever a shopper names a size while browsing ("hoodies in medium?", "Yale Mom stuff in a small").
- Code: `tools.find_in_size` (shares its ranking with `search_products`), registered in `agent.py`, result type `SizeHit` in `models.py`.

**Why it helps**
- **Faster and cheaper:** before, "hoodies in medium" meant a search plus a `check_stock` call for each product: up to 7 tool calls and model round-trips. Now it's 1, so the reply comes back sooner and costs less.
- **More accurate:** Will can't recommend something the shopper can't buy in their size, and the numbers come straight from the database.
- **Shopper:** a direct answer to the question they actually asked.

## 4. Find similar items: `find_similar` (agent)

**What was added**
- A new agent tool, `find_similar(product_id, color, size)`. It returns 2–4 close alternatives to a product, each with `why_similar` ("same type (Hoodies)", "same line: left chest", shared themes).
- It can require a **color** the shopper wants and/or a **size in stock**.
- Similarity is scored from the database: same kind of item, same product line (shared name words like "Left Chest" or "Tri Blend Sports"), shared tags (sport, college, family line) and shared colors.
- `prompt.md` tells Will never to leave a shopper at a dead end. When something is sold out in their size or doesn't come in their color, he says so plainly, then offers alternatives from `find_similar` and briefly says why each is close.
- Code: `tools.find_similar`, registered in `agent.py`, result type `SimilarHit` in `models.py`.

**Why it helps**
- **Shopper:** "Fencing hoodie in large? Sold out." used to end the conversation. Now it continues: "…but the Squash and Volleyball Left Chest hoodies are the same look, and both have your large."
- **Business:** a sold-out size or a missing color becomes a sale of something similar instead of a lost customer. It also moves stock in sizes that are piling up.
- **Accuracy:** every alternative is a real product in stock, picked by rules over the database rather than guessed by the model.

---

## Checks run (Oct 22, 2026; stand-in model first, then live on the Mac)

| Check | Result |
|---|---|
| Home page shows 7 "Shop for…" tiles with counts (Mom 2, Dad 3, Grandparents 3, Family 4, Residential Colleges 19, Grad & Professional 13, Athletes & Fans 34) | ✅ |
| Tap "For Mom" → `/products?for=mom`, title "Shop For Mom", 2 items | ✅ |
| Add My size = M → "2 items in stock in M for Mom", both cards tagged "M: in stock" | ✅ |
| Hoodies + M → 21 items, 7 tagged "only N left" | ✅ |
| Reload the page → M is still selected | ✅ |
| Open a product → its page starts on size M ("M: Only a few left (5 available)") | ✅ |
| Will, "got hoodies in medium?" → one `find_in_size` call, only hoodies in stock in M, with counts | ✅ |
| Will, Fencing hoodie in large (sold out) → `find_similar` returns Crew, Squash and Volleyball Left Chest hoodies + Diving Left Chest crewneck, all with large in stock | ✅ |
| `find_similar` for the Basic Hoodie in gray → only items that come in gray | ✅ |
| **Live, real model:** "Got any hoodies in medium?" → 6 cards, every one in stock in M (5–20 each, checked against the database) | ✅ |
| **Live, real model:** on the Basic Hoodie page, "Do you have this in grey?" → plain no, the colors it does come in, then 4 gray hoodies from `find_similar` (after the grey/gray fix) | ✅ |
| **Live:** My size = M on Hoodies → "21 items in stock in M" with stock tags (screenshot: `app_check_images/usability_my_size.png`) | ✅ |
