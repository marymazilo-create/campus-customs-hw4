# Design: "The club room" (Problem 10)

**Inspiration:** the warmth of the Yale Club of New York (wood-paneled library, an elegant old-style serif, italic captions) and the Polo Bar in New York (mahogany walls, gilt-framed portraits under picture lights, deep green and brass). The goal: walking onto the site should feel like walking into a members' club that happens to sell Yale gear, not like a template.

Before → after: `design_images/before_home.png` (bright navy gradient, default sans-serif, floating white squares) and `design_images/after_wills_picks.png` (framed products, green-felt "Will's picks" table, mahogany chat).

## What changed, and why it should help people stay and buy

### 1. Color: from bright web navy to a club palette
| Token | Hex | Used for |
|---|---|---|
| Mahogany | `#3B2116` | Paneled hero wall, footer, chat header |
| Library green | `#1E3A2F` | Buttons, active filters, announcement strip, "Will's picks" table |
| Brass | `#B48A4A` / `#D9BE84` | Picture frames, rules, captions, focus rings |
| Linen | `#F2ECDF` | Page background (instead of stark white) |
| Yale blue | `#0F2D52` | Kept for prices and links, so the shop is still unmistakably Yale |

**Why:** warm, dark woods and greens read as heritage and quality, which suits $58–$98 sweatshirts and gift buyers (parents, grandparents, alumni). Keeping Yale blue for prices ties the money moment to the brand.

### 2. Fonts: a voice for the shop, a workhorse for buttons
- **Libre Caslon Display** for headlines, product names and the wordmark: an 18th-century-style serif like the Yale Club's, and close to what would have been on a New Haven shop sign.
- **Libre Caslon Text, italic** for small labels and captions ("Officially licensed Yale gear, 57 Broadway", "Hoodies", "My size"), replacing the shouty ALL-CAPS labels.
- **Figtree** (clean sans-serif) for body text, buttons, filters and chat, so everything clickable stays easy to read.

**Why:** the serif gives the shop personality and trust; the sans keeps shopping fast. One voice, one workhorse, no clutter.

### 3. Visual hierarchy: the paneled wall comes first
- The home page opens on a **mahogany paneled wall** (CSS stripes and a warm light glow, no stock photo) with a large Caslon headline, "Yale, worn well since 1973."
- The shop's three favorites hang on the wall as **gilt-framed portraits**: frame, linen mat, a brass picture light on top, and an italic caption with the product name. Each frame links to that product.
- One primary button (green with a brass edge, "Shop all gear") and one quiet secondary ("Our story").

**Why:** the first screen tells you this is a heritage Yale shop and shows real products right away; the eye goes headline → products → one clear next step.

### 4. Product presentation: every product is a framed portrait
- Product cards, category tiles, "Shop for…" tiles and the product page photo all use the **same gilt frame + linen mat**. The name sits underneath like a museum plaque (italic category, Caslon name, Yale-blue price).
- The product page shows **one large framed portrait** next to the details.
- Stock tags ("L: only 5 left") are now thin outlined labels that match the frames.

**Why:** framing makes simple product photos (many on black or white backgrounds) look curated and consistent, and makes every item feel like it's worth more, which supports the price point.

### 5. The chat interface: Will at the bar
- Chat button: mahogany with a brass edge and italic "Chat with us."
- Chat panel: paneled mahogany header with a **"W" monogram** for Will in a green-and-brass medallion; his messages on linen with a brass edge; the shopper's in library green; typing shows "Will is checking the back room…".
- **"Will's picks"** now sits on a **green-felt card table** with a brass inlay, so it's obvious these came from the chat.

**Why:** Will is the sarcastic manager's cousin; giving him a recognizable "spot at the bar" makes the chat feel like part of the store, so shoppers are more likely to use it, and products he recommends stand out on the page.

### 6. Motion: the secret door, then one moment on purpose
- **The bookcase door (first visit only).** On a shopper's first visit to the Home page, the shop is hidden behind a **library bookcase**: five shelves of leather-bound spines in oxblood, green, navy and tan with gold bands, a few books leaning, and a brass plaque reading "Campus Customs, on Broadway since 1973." After a short beat (0.9 s) the whole bookcase **slides sideways like a secret door** (1.2 s), revealing the paneled wall and the framed favorites behind it. The bookcase is drawn in code, not a photo, so it loads instantly and is entirely our own.
  - **Guardrails:** plays **once per visit** (remembered for the browser session); a **Skip** button, and **Esc, any key, a click or scrolling** open it immediately; the slide itself is **1.2 seconds**; it **never plays** for shoppers with "reduce motion" turned on, or when someone lands directly on another page (a product link, say); the drawing is hidden from screen readers, so they go straight to the shop.
  - **Why:** it turns arriving into a small moment of delight that matches the club-room story ("you've been let into the back library"), which makes the site memorable and more likely to be shared or revisited. The guardrails keep it from ever getting in the way of shopping.
- After that, the only movement is tied to the shopper: when Will puts picks on the page, the framed products are **hung one by one**: each drops in slightly, swings, and settles (staggered about 0.08 s apart).
- Frames get a soft brass glow on hover/focus; nothing else moves on its own.
- All of it is turned off for people who set "reduce motion" on their device.

**Why:** a single, meaningful animation draws the eye to exactly what the shopper asked for, without making the site feel busy.

## What stayed the same (on purpose)
- Layout, filters ("My size", "Shop for"), search and all features from Problems 3–9 work as before; this was a visual change only.
- Keyboard focus is visible (brass outline) and text contrast stays high (dark ink on linen, linen on mahogany/green).

## Files
`frontend/index.html` (fonts, brass-on-mahogany favicon), `frontend/src/index.css` ("Problem 10: The club room" section), `frontend/src/pages/Home.tsx` (paneled hero with framed favorites), `frontend/src/components/ChatWidget.tsx` (Will's monogram, typing line), `frontend/src/components/NavBar.tsx` (italic "Campus Customs on Broadway"), `frontend/src/components/BookcaseDoor.tsx` + `App.tsx` (the secret door). Screenshot: `design_images/after_bookcase_door.png`.
