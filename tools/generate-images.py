#!/usr/bin/env python3
"""
Generate site imagery via kie.ai nano-banana (Gemini 2.5 Flash Image).

Reads KIE_API_KEY from .env (or environment). Creates tasks in parallel,
polls each until done, downloads JPEGs into assets/img/.

Re-run any time to regenerate. Existing files are overwritten.
Pass --only <slot> to regenerate a single image.
"""
import os, sys, json, time, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "assets" / "img"
ENV_FILE = ROOT / ".env"

# Shared brand/architecture guidance appended to every prompt.
ZIM = (
    " Photographic editorial quality. Setting: upmarket gated residential estate in Harare, "
    "Zimbabwe (Highveld). Zimbabwean architectural vernacular: single- or double-storey homes "
    "with face-brick or warm whitewashed plastered walls, low-pitched terracotta Marley-tile "
    "roofs, wide verandahs and stoeps, timber-framed windows, security walls with wrought-iron "
    "gates. Mature indigenous landscaping: jacaranda, msasa, flamboyant trees, strelitzia, "
    "aloes, plumbago, bougainvillea, clipped buxus hedges, kikuyu or LM buffalo lawn, "
    "stone-edged beds. Warm afternoon or golden-hour Highveld light (unless specified). "
    "Grounded, premium-but-not-flashy aesthetic; established, well-maintained. "
    "No visible text, no logos, no watermarks, no signage, no stock-photo feel. "
    "Natural composition, shallow depth of field where appropriate."
)

JOBS = [
    # ===== HOME HERO =====
    {"slot": "hero", "size": "16:9", "prompt":
        "Wide cinematic exterior view of an upmarket Harare gated residential estate at golden hour. "
        "A single-storey face-brick home with a low-pitched terracotta-tile roof and deep verandah "
        "sits mid-ground, framed by mature jacaranda and msasa trees. A manicured emerald kikuyu "
        "lawn sweeps the foreground, stone-edged beds of strelitzia and aloes to one side. "
        "Long warm shadows, crisp Highveld air." + ZIM},

    # ===== SERVICE CARDS (home page) =====
    {"slot": "service-landscaping", "size": "16:9", "prompt":
        "Mature landscaped private garden on a Harare estate: crisply edged emerald kikuyu lawn, "
        "hand-laid flagstone pathway curving through stone-bordered beds of aloes, strelitzia and "
        "plumbago, clipped buxus hedge, portion of a face-brick home with terracotta-tile roof "
        "visible in soft focus background. Late afternoon golden light." + ZIM},

    {"slot": "service-maintenance", "size": "16:9", "prompt":
        "A uniformed maintenance technician in a forest-green branded work shirt, three-quarter "
        "from behind, on a short ladder inspecting the guttering of a single-storey Harare "
        "face-brick home with terracotta-tile roof. Tidy tool bag on the paved verandah stoep. "
        "No face prominent. Competent, professional. Soft warm afternoon light." + ZIM},

    {"slot": "service-painting", "size": "16:9", "prompt":
        "Close-to-medium shot: a painter's hand with a fine brush finishing a crisp forest-green "
        "painted timber window frame against a freshly-painted warm off-white plastered wall on "
        "a Harare residential home. Subtle dust-sheet on paved stoep below. Immaculate finish, "
        "precise brushwork. Highveld afternoon sunlight catching fresh paint sheen." + ZIM},

    {"slot": "service-solar", "size": "16:9", "prompt":
        "Dusk view down a tree-lined tarmac road inside a gated residential community in Harare. "
        "A row of modern black solar-powered street lamp-posts (slim, minimal, with small solar "
        "panels on top) glow warm-white on either side of the road. Security walls and wrought-iron "
        "gates of estate homes visible, face-brick pillars. Deep blue-violet twilight sky, "
        "silhouetted jacaranda canopy, warm amber pools of lamp-light on the tarmac." + ZIM},

    {"slot": "service-project", "size": "16:9", "prompt":
        "On-site project coordination at a Harare estate renovation: a project manager in a "
        "forest-green branded shirt, three-quarter from behind, holding a tablet, standing on a "
        "newly-laid flagstone driveway. A multi-discipline crew in soft focus behind — a "
        "landscaper planting a hedge, a painter on a short ladder near a face-brick wall. "
        "Calm, organised. Warm afternoon light." + ZIM},

    # ===== SERVICE PAGE HEROES (banners) =====
    {"slot": "hero-landscaping", "size": "16:9", "prompt":
        "Sweeping low-angle view down a manicured Harare estate lawn at golden hour. In the "
        "foreground a stone-edged bed of aloes and strelitzia, mid-ground rolling kikuyu lawn "
        "with a flagstone path, background a single-storey face-brick home with a terracotta-tile "
        "roof and verandah framed by jacaranda trees. Long warm shadows, raking golden light." + ZIM},

    {"slot": "hero-maintenance", "size": "16:9", "prompt":
        "Wide view of a single-storey Harare estate home: face-brick walls, terracotta-tile roof, "
        "verandah. A uniformed maintenance crew of two in forest-green branded shirts at work — "
        "one on a ladder adjusting guttering, another on the stoep checking a door frame. "
        "Branded tool-van parked on the driveway. Calm, professional. Soft afternoon light." + ZIM},

    {"slot": "hero-painting", "size": "16:9", "prompt":
        "Wide view of a freshly-painted single-storey Harare estate home exterior: warm off-white "
        "plastered walls, forest-green painted timber window frames and stoep trim, terracotta-tile "
        "roof. A painter in protective gear on a modern aluminium mobile scaffold tower (proper "
        "metal tube-and-clamp construction, with safety railings and a boarded working platform) "
        "finishing the upper wall. Dust sheets neatly placed below. Crisp Highveld afternoon "
        "sunlight. The scaffolding is clearly metal — no bamboo, no timber poles." + ZIM},

    {"slot": "hero-solar", "size": "16:9", "prompt":
        "Elevated wide view down a long tree-lined tarmac street inside a gated residential "
        "community in Harare at dusk. Rows of modern black solar-powered street lamp-posts "
        "casting warm amber pools on the road. Security walls, wrought-iron gates and face-brick "
        "pillars of estate homes visible either side. Jacaranda canopy silhouetted against a "
        "deep blue-violet twilight sky." + ZIM},

    {"slot": "hero-project", "size": "16:9", "prompt":
        "Wide view of a multi-discipline renovation on a Harare estate: modern aluminium "
        "tube-and-clamp metal scaffolding (proper industrial scaffolding with safety railings and "
        "boarded platforms, clearly metal — no bamboo, no timber poles) erected against a "
        "face-brick façade. Fresh flagstone paving being laid in the foreground, a landscape crew "
        "planting a hedge, a project manager and foreman consulting plans on a tablet. Organised "
        "activity, materials neatly arranged. Warm late-afternoon light." + ZIM},

    # ===== LANDSCAPING GALLERY (6) =====
    {"slot": "gallery-landscaping-1", "size": "4:3", "prompt":
        "Close composition: crisply-edged kikuyu lawn meeting a stone-bordered planting bed of "
        "aloes and strelitzia on a Harare estate, jacaranda shade dappling the edge, "
        "Highveld afternoon light." + ZIM},

    {"slot": "gallery-landscaping-2", "size": "4:3", "prompt":
        "Indigenous Highveld planting scheme on a Harare estate: strelitzia, aloes, agapanthus, "
        "clipped buxus hedge, decorative stone mulch. Soft afternoon light." + ZIM},

    {"slot": "gallery-landscaping-3", "size": "4:3", "prompt":
        "Irregular-granite flagstone pathway set into kikuyu lawn, curving gently through a "
        "landscaped Harare garden, low clipped hedge lining one side, afternoon sun." + ZIM},

    {"slot": "gallery-landscaping-4", "size": "4:3", "prompt":
        "Pop-up irrigation sprinkler head active on a manicured Harare estate lawn, a fine mist "
        "catching afternoon Highveld light, stone-edged bed in soft focus behind." + ZIM},

    {"slot": "gallery-landscaping-5", "size": "4:3", "prompt":
        "Crisply clipped buxus hedge and shaped topiary lining the flagstone driveway of a "
        "Harare estate, face-brick garden wall in the background, warm golden light." + ZIM},

    {"slot": "gallery-landscaping-6", "size": "4:3", "prompt":
        "Hardscape detail on a Harare estate: low dry-stone retaining wall with a terraced "
        "planting bed of aloes and succulents above, stone steps to one side, afternoon light." + ZIM},

    # ===== MAINTENANCE GALLERY (6) =====
    {"slot": "gallery-maintenance-1", "size": "4:3", "prompt":
        "Close-up of a plumber's gloved hands fitting a new copper compression joint under a "
        "kitchen sink, tools neatly arranged, clean work." + ZIM},

    {"slot": "gallery-maintenance-2", "size": "4:3", "prompt":
        "Uniformed electrical technician in a forest-green shirt, viewed from behind, checking "
        "a residential distribution board mounted on a white plastered wall, small tool bag "
        "on the floor." + ZIM},

    {"slot": "gallery-maintenance-3", "size": "4:3", "prompt":
        "Roofer inspecting terracotta Marley roof tiles on the pitched roof of a single-storey "
        "Harare home, safety harness visible, Highveld afternoon light." + ZIM},

    {"slot": "gallery-maintenance-4", "size": "4:3", "prompt":
        "Close composition of a freshly restored timber front door on a Harare face-brick home: "
        "a solid stained-timber panelled door with polished brass handle, set in a deep timber "
        "frame, warm afternoon light raking the grain, no hands or people visible — just the "
        "completed craftsmanship. Background softly blurred verandah stoep." + ZIM},

    {"slot": "gallery-maintenance-5", "size": "4:3", "prompt":
        "Uniformed technician in forest-green shirt cleaning guttering on a single-storey Harare "
        "home with a terracotta-tile roof, standing on a short ladder, debris collected in a "
        "bucket on the stoep below." + ZIM},

    {"slot": "gallery-maintenance-6", "size": "4:3", "prompt":
        "Estate groundskeeper with a clipboard doing a scheduled walkthrough of a manicured "
        "Harare garden, viewed from behind in a forest-green branded shirt, calm thorough "
        "inspection, afternoon light." + ZIM},

    # ===== PAINTING GALLERY (6) =====
    {"slot": "gallery-painting-1", "size": "4:3", "prompt":
        "Close-to-medium shot of a professional painter in protective overalls, respirator mask "
        "and cap, using a handheld airless spray gun to apply a warm off-white coat to the "
        "plastered exterior wall of a Harare estate home. A compact yellow-and-black professional "
        "airless sprayer machine on wheels (cylindrical motor housing with a paint hopper on top, "
        "pressure hose snaking to the gun) sits in frame beside a dust sheet. Fine even spray "
        "mist catching afternoon light. No visible text or brand logos on the machine. "
        "Crisp industrial detail." + ZIM},

    {"slot": "gallery-painting-2", "size": "4:3", "prompt":
        "Surface preparation: a painter's hand with a scraper removing flaking old paint from a "
        "timber window frame on a Harare home, dust sheet below, even diffuse light." + ZIM},

    {"slot": "gallery-painting-3", "size": "4:3", "prompt":
        "Interior feature wall painted in a deep forest-green against warm off-white adjoining "
        "walls in a Harare home sitting room, simple timber furnishings, afternoon light through "
        "a window." + ZIM},

    {"slot": "gallery-painting-4", "size": "4:3", "prompt":
        "Detail shot: precise brush finishing the edge of a terracotta-clay painted timber door "
        "frame against a whitewashed plastered wall on a Harare verandah stoep." + ZIM},

    {"slot": "gallery-painting-5", "size": "4:3", "prompt":
        "Wide view of the freshly-painted façade of a single-storey Harare estate home: "
        "crisp warm off-white walls, forest-green timber trim, tile roof, stoep in foreground, "
        "warm afternoon light." + ZIM},

    {"slot": "gallery-painting-6", "size": "4:3", "prompt":
        "Decorative render finish on an exterior wall of a Harare estate: subtly textured "
        "plaster in a warm cream tone, afternoon shadows catching the texture." + ZIM},

    # ===== SOLAR LIGHTING GALLERY (6) — gated community street lighting focus =====
    {"slot": "gallery-solar-1", "size": "4:3", "prompt":
        "Tree-lined gated-community street in Harare at dusk, a row of modern black "
        "solar-powered street lamp-posts glowing warm-white, face-brick pillars and "
        "wrought-iron security gates visible either side." + ZIM},

    {"slot": "gallery-solar-2", "size": "4:3", "prompt":
        "Close view of a modern black solar-powered street lamp-post with a small solar panel "
        "on top and a warm-white LED head, leafy jacaranda canopy in soft focus behind at dusk." + ZIM},

    {"slot": "gallery-solar-3", "size": "4:3", "prompt":
        "Security perimeter wall of a Harare estate at dusk with solar flood lights mounted on "
        "face-brick columns, warm glow on the wall, silhouetted trees above." + ZIM},

    {"slot": "gallery-solar-4", "size": "4:3", "prompt":
        "Landscaped garden pathway inside a Harare estate at dusk, a row of low solar bollards "
        "lining a flagstone path, warm amber glow, shrubs softly up-lit." + ZIM},

    {"slot": "gallery-solar-5", "size": "4:3", "prompt":
        "Wrought-iron driveway gate of a Harare estate at dusk, solar-powered gate-pillar lamps "
        "glowing warm on face-brick pillars either side of the gate." + ZIM},

    {"slot": "gallery-solar-6", "size": "4:3", "prompt":
        "Feature lighting illuminating a mature msasa tree on a Harare estate at dusk, "
        "warm-gold uplights casting light up into the canopy, residence in soft focus behind." + ZIM},

    # ===== PROJECT DELIVERY GALLERY (6) =====
    {"slot": "gallery-project-1", "size": "4:3", "prompt":
        "Project manager in a forest-green branded shirt reviewing plans on a tablet with a "
        "foreman, on-site at a Harare estate. Background: modern aluminium tube-and-clamp metal "
        "scaffolding (industrial with safety railings and boarded platforms — clearly metal, "
        "absolutely no bamboo, no timber poles, no rope lashings) erected against a face-brick "
        "wall." + ZIM},

    {"slot": "gallery-project-2", "size": "4:3", "prompt":
        "Multi-discipline on-site scene: a landscaper planting a hedge in mid-ground, a painter "
        "on a short ladder near a face-brick wall in background, organised materials foreground, "
        "Harare estate setting." + ZIM},

    {"slot": "gallery-project-3", "size": "4:3", "prompt":
        "Handover moment: two professionals in forest-green shirts shaking hands with a smiling "
        "homeowner in front of a completed Harare estate renovation, warm afternoon light." + ZIM},

    {"slot": "gallery-project-4", "size": "4:3", "prompt":
        "Procurement and materials: neatly arranged stacks of pavers, bags of cement, and timber "
        "on a tarp beside a face-brick construction area on a Harare estate, organised." + ZIM},

    {"slot": "gallery-project-5", "size": "4:3", "prompt":
        "Mid-project progress shot of a Harare estate: new flagstone paving partially laid, "
        "fresh hedging planted, modern aluminium tube-and-clamp metal scaffolding (industrial "
        "with safety railings and boarded platforms, clearly metal — no bamboo, no timber poles) "
        "erected against a face-brick façade, workers at tasks, afternoon light." + ZIM},

    {"slot": "gallery-project-6", "size": "4:3", "prompt":
        "Wide completed-project view: a restored single-storey Harare estate home with "
        "face-brick walls, terracotta-tile roof, fresh forest-green trim, manicured lawns and "
        "planting, golden-hour light." + ZIM},

    # ===== MONOGRAM VARIATIONS (expanded from winning Concept 1) =====
    {"slot": "logo-concept-1a", "size": "1:1", "prompt":
        "A premium heritage brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: three letters composed together — an italic serif capital 'S' in deep "
        "forest-green (#2E5E3E) on the left, an elegant serif ampersand '&' in terracotta "
        "(#C4834A) in the centre, and an italic serif capital 'D' in deep forest-green (#2E5E3E) "
        "on the right. All three letters sit at the same baseline, balanced in size, with "
        "tasteful serif detailing like Playfair Display or a classical Didone typeface. "
        "The composition sits inside a thin harvest-gold (#B8973C) circular outline (single "
        "hairline ring). Minimal, refined, heritage engraved feel. Flat vector aesthetic, "
        "sharp edges. No photograph, no texture, no shadow. No other text, no watermark."},

    {"slot": "logo-concept-1b", "size": "1:1", "prompt":
        "A premium heritage brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: an interlocking monogram ligature of capital letters 'S' and 'D', drawn "
        "as a single intertwined mark — the curves of the S and the straight stem of the D "
        "share strokes or overlap elegantly. The S is in deep forest-green (#2E5E3E), the D in "
        "terracotta (#C4834A), with the shared/overlapping stroke rendered in a warm blend. "
        "Classical serif letterforms, engraved heritage feel. The ligature sits inside a thin "
        "harvest-gold (#B8973C) circular outline (single hairline ring). Flat vector aesthetic, "
        "sharp crisp edges. No photograph, no texture, no shadow. No other text, no watermark."},

    {"slot": "logo-concept-1c", "size": "1:1", "prompt":
        "A premium heritage brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: a large bold italic serif capital letter 'S' in deep forest-green (#2E5E3E) "
        "as a single solo mark — classical Didone / Playfair Display style, with refined serif "
        "terminals and tasteful thick-and-thin contrast. A single thin harvest-gold (#B8973C) "
        "circular outline (hairline ring) frames the letter, with a small solid terracotta "
        "(#C4834A) dot or diamond set tastefully at the 6 o'clock position on the ring as a "
        "heritage accent. Minimal, engraved, refined. Flat vector aesthetic, sharp edges. "
        "No photograph, no texture, no shadow. No other text, no watermark."},

    {"slot": "logo-concept-1d", "size": "1:1", "prompt":
        "A premium heritage brand-seal logo on a warm off-white (#F7F4EF) square background. "
        "Centered: a large italic serif capital letter 'S' in deep forest-green (#2E5E3E) in "
        "the middle. Around the inside of the outer ring, the wordmark 'SCAPES & DÉCOR' is set "
        "in small caps (all capitals) in deep charcoal (#22281E) arcing around the top of the "
        "ring, and the text 'EST. 2014' in small caps arcing around the bottom of the ring, "
        "separated from the top text by a small terracotta (#C4834A) dot on each side of the "
        "ring at 3 and 9 o'clock. Two concentric thin harvest-gold (#B8973C) circular outlines "
        "(hairline rings) frame the composition. Classical heritage seal, engraved aesthetic. "
        "Crisp sharp text, flat vector, no photograph, no texture, no shadow. No other text."},

    # ===== LOGO CONCEPTS (square, for reference — will be hand-coded as SVG) =====
    {"slot": "logo-concept-1", "size": "1:1", "prompt":
        "A premium heritage brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: a large italic serif capital letter 'S' in deep forest-green (#2E5E3E), "
        "with an elegant serif ampersand '&' in terracotta (#C4834A) set tastefully beside "
        "or below the S. The mark sits inside a thin harvest-gold (#B8973C) circular outline "
        "(single hairline ring). Minimal, refined, hand-engraved feel, subtle embossed depth. "
        "Flat vector aesthetic, sharp edges. No photograph, no texture, no shadow. "
        "No additional text, no watermark. Clean studio composition."},

    {"slot": "logo-concept-2", "size": "1:1", "prompt":
        "A premium minimal brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: a simple geometric silhouette of a classical round-topped arched doorway "
        "(just the arch opening — an archway portal, not a whole house) in deep forest-green "
        "(#2E5E3E), with a terracotta (#C4834A) solid keystone detail at the top centre of the "
        "arch. The arch sits inside a thin harvest-gold (#B8973C) circular outline (single "
        "hairline ring). Minimal, architectural, refined. Flat vector aesthetic, crisp geometric "
        "edges. No photograph, no texture, no 3D shading. No text. Clean studio composition."},

    {"slot": "logo-concept-3", "size": "1:1", "prompt":
        "A premium minimal brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: a single stylized silhouette of a mature jacaranda-style tree with a broad "
        "canopy on a slim trunk, in deep forest-green (#2E5E3E). A thin horizontal ground-line "
        "in terracotta (#C4834A) passes just beneath the tree base. The tree sits inside a thin "
        "harvest-gold (#B8973C) circular outline (single hairline ring). Minimal, elegant, "
        "estate-feeling. Flat vector aesthetic, crisp silhouette, no texture, no photograph, "
        "no 3D shading. No text. Clean studio composition."},

    {"slot": "logo-concept-4", "size": "1:1", "prompt":
        "A premium minimal brand mark logo on a warm off-white (#F7F4EF) square background. "
        "Centered: three thin, gently curving horizontal lines suggesting layered landscape hills "
        "— the top line in harvest-gold (#B8973C), the middle in terracotta (#C4834A), the "
        "bottom in deep forest-green (#2E5E3E). A small solid terracotta dot (like a sun or a "
        "marker) sits tastefully above the top curve. The composition sits inside a thin "
        "forest-green circular outline (single hairline ring). Minimal, abstract, estate-feeling. "
        "Flat vector aesthetic, clean lines, no texture, no photograph, no shading. "
        "No text. Clean studio composition."},

    # ===== ABOUT VISUAL (portrait) =====
    {"slot": "about", "size": "3:4", "prompt":
        "Portrait-orientation: a small team of three in forest-green branded work shirts "
        "standing casually in front of an established single-storey Harare face-brick residence "
        "with terracotta-tile roof, a jacaranda tree dappling them with afternoon light, "
        "faces softly averted or in three-quarter profile. Competent, grounded, approachable." + ZIM},
]


def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())
    key = os.environ.get("KIE_API_KEY")
    if not key:
        sys.exit("KIE_API_KEY missing. Put it in .env or export it.")
    return key


def http(method, url, headers=None, body=None, timeout=90):
    cmd = ["curl", "-sS", "--max-time", str(timeout), "-X", method, url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if body is not None:
        cmd += ["--data", json.dumps(body)]
    out = subprocess.check_output(cmd)
    return json.loads(out.decode())


def download_binary(url, dest, timeout=120):
    subprocess.check_call(["curl", "-sS", "--max-time", str(timeout), "-o", str(dest), url])


def create_task(key, prompt, size):
    return http(
        "POST",
        "https://api.kie.ai/api/v1/jobs/createTask",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        body={
            "model": "google/nano-banana",
            "input": {
                "prompt": prompt,
                "image_size": size,
                "output_format": "jpeg",
            },
        },
    )


def poll_task(key, task_id, max_wait=240):
    start = time.time()
    while time.time() - start < max_wait:
        r = http(
            "GET",
            f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}",
            headers={"Authorization": f"Bearer {key}"},
        )
        state = r.get("data", {}).get("state")
        if state == "success":
            result = json.loads(r["data"]["resultJson"])
            return result["resultUrls"][0]
        if state in ("fail", "failed", "error"):
            raise RuntimeError(f"task {task_id} failed: {r}")
        time.sleep(2)
    raise TimeoutError(f"task {task_id} did not complete within {max_wait}s")


def main():
    key = load_env()
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]

    jobs = [j for j in JOBS if only is None or j["slot"] == only]
    if not jobs:
        sys.exit(f"no job matched slot '{only}'")

    # Create tasks (small stagger to avoid rate limits)
    print(f"Creating {len(jobs)} tasks...")
    for job in jobs:
        r = create_task(key, job["prompt"], job["size"])
        job["task_id"] = r["data"]["taskId"]
        print(f"  {job['slot']:32s} → {job['task_id']}")
        time.sleep(0.3)

    # Poll + download each
    print("\nPolling + downloading...")
    ok = fail = 0
    for job in jobs:
        try:
            url = poll_task(key, job["task_id"])
            dest = IMG_DIR / f"{job['slot']}.jpg"
            download_binary(url, dest)
            kb = dest.stat().st_size // 1024
            print(f"  {job['slot']:32s} ✓ {kb}KB")
            ok += 1
        except Exception as e:
            print(f"  {job['slot']:32s} ✗ {e}")
            fail += 1

    # Manifest for future regeneration
    manifest = {j["slot"]: {"prompt": j["prompt"], "size": j["size"]} for j in JOBS}
    (IMG_DIR / "prompts.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nDone. {ok} succeeded, {fail} failed. Images in {IMG_DIR}")


if __name__ == "__main__":
    main()
