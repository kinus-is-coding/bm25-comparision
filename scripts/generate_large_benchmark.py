# generate_large_benchmark.py
import json
import random
import copy

# Distractors: hoàn toàn không liên quan đến 10 query
DISTRACTORS = [
    {
        "video_id": "cooking_pasta_tutorial",
        "timestamp": "00:02:15",
        "ocr": "How to Cook Perfect Pasta",
        "asr": "Today we show you the secrets to making restaurant-quality pasta at home with simple ingredients.",
        "vlm_caption": "A chef stirs a pot of boiling water with spaghetti in a bright kitchen. Steam rises and fresh herbs are visible on the counter.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "gardening_tips_spring",
        "timestamp": "00:05:30",
        "ocr": "Spring Gardening — Planting Tomatoes",
        "asr": "Expert gardener explains how to plant tomato seedlings in your backyard garden for the best harvest.",
        "vlm_caption": "A person kneels in a garden bed, placing small green plants into rich dark soil. Gardening tools and a watering can sit nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "yoga_morning_routine",
        "timestamp": "00:08:00",
        "ocr": "10 Minute Morning Yoga Flow",
        "asr": "Follow along with this gentle morning yoga sequence to wake up your body and mind for the day ahead.",
        "vlm_caption": "A person in athletic wear performs yoga poses on a mat in a sunlit room. Plants and candles create a peaceful atmosphere.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "bitcoin_price_analysis",
        "timestamp": "00:12:45",
        "ocr": "Bitcoin Technical Analysis — Weekly Chart",
        "asr": "Crypto analyst reviews Bitcoin price action, identifying key support and resistance levels for the coming week.",
        "vlm_caption": "A person points at a computer screen showing candlestick charts and price graphs. Multiple monitors display trading data.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "puppy_training_basics",
        "timestamp": "00:03:20",
        "ocr": "Puppy Training 101 — Sit and Stay",
        "asr": "Professional dog trainer demonstrates how to teach your new puppy basic commands using positive reinforcement techniques.",
        "vlm_caption": "A small fluffy puppy sits on a training mat while a person holds a treat. The puppy looks up attentively with its ears perked.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "home_workout_no_equipment",
        "timestamp": "00:06:10",
        "ocr": "Full Body Workout — No Equipment Needed",
        "asr": "Fitness coach leads a 20-minute full body workout you can do at home without any gym equipment.",
        "vlm_caption": "An athletic person performs jumping jacks and push-ups in a living room. A yoga mat is on the floor and a water bottle sits nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "travel_vlog_japan",
        "timestamp": "00:15:30",
        "ocr": "Japan Travel Vlog — Kyoto Temples",
        "asr": "We explore the beautiful temples and shrines of Kyoto, sharing travel tips and hidden gems for your Japan trip.",
        "vlm_caption": "A person walks through a traditional Japanese garden with red torii gates. Cherry blossom trees frame a stone path.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "makeup_tutorial_natural",
        "timestamp": "00:04:50",
        "ocr": "Natural Makeup Look — Everyday Tutorial",
        "asr": "Makeup artist shows how to achieve a natural everyday look using minimal products for a fresh appearance.",
        "vlm_caption": "A person applies makeup in front of a mirror with ring lights. Brushes and cosmetic products are arranged on a vanity table.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "car_maintenance_oil_change",
        "timestamp": "00:09:15",
        "ocr": "DIY Oil Change — Car Maintenance Guide",
        "asr": "Mechanic demonstrates how to change your car's engine oil safely at home with basic tools and supplies.",
        "vlm_caption": "A person works under a car in a garage, using a wrench to remove a drain plug. An oil pan sits on the concrete floor.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "piano_lesson_beginner",
        "timestamp": "00:07:00",
        "ocr": "Piano Lessons for Beginners — First Chords",
        "asr": "Music teacher explains basic piano chords and finger placement for absolute beginners starting their musical journey.",
        "vlm_caption": "Hands press keys on a black piano keyboard. Sheet music rests on the stand and a metronome ticks in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "real_estate_investing",
        "timestamp": "00:11:20",
        "ocr": "Real Estate Investing for Beginners",
        "asr": "Financial advisor explains how to start investing in rental properties and build passive income through real estate.",
        "vlm_caption": "A person stands in front of a modern apartment building, gesturing toward the property. Blueprints and financial charts are visible.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "sushi_rolling_technique",
        "timestamp": "00:05:45",
        "ocr": "How to Roll Sushi Like a Chef",
        "asr": "Sushi master demonstrates the proper technique for rolling maki and nigiri at home with fresh ingredients.",
        "vlm_caption": "Hands carefully place fish and rice on a bamboo mat, then roll and slice the sushi into even pieces on a wooden board.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "meditation_guided_sleep",
        "timestamp": "00:20:00",
        "ocr": "Guided Sleep Meditation — Fall Asleep Fast",
        "asr": "Relaxing guided meditation to help you fall asleep quickly and achieve deep restorative sleep tonight.",
        "vlm_caption": "A person lies in bed with eyes closed in a dimly lit bedroom. Soft blue light and calming nature sounds create a peaceful scene.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "skateboarding_tricks_beginner",
        "timestamp": "00:04:30",
        "ocr": "5 Easy Skateboard Tricks for Beginners",
        "asr": "Pro skater teaches five fundamental tricks that every beginner should learn to start skateboarding confidently.",
        "vlm_caption": "A person rides a skateboard in a concrete skate park, performing an ollie over a small ramp. Other skaters watch in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "interior_design_minimalist",
        "timestamp": "00:08:40",
        "ocr": "Minimalist Home Design Ideas",
        "asr": "Interior designer shares tips for creating a clean minimalist living space with functional furniture and neutral colors.",
        "vlm_caption": "A bright living room with white walls, a gray sofa, and a single large plant. Natural light streams through floor-to-ceiling windows.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "fishing_river_bass",
        "timestamp": "00:10:15",
        "ocr": "Bass Fishing Tips — River Techniques",
        "asr": "Experienced angler shares techniques for catching bass in rivers, including lure selection and casting strategies.",
        "vlm_caption": "A person stands in a shallow river holding a fishing rod. The water flows around their waders and trees line the riverbank.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "language_learning_spanish",
        "timestamp": "00:06:30",
        "ocr": "Learn Spanish — Common Phrases for Travel",
        "asr": "Language teacher teaches essential Spanish phrases for travelers, covering greetings, directions, and restaurant ordering.",
        "vlm_caption": "A person writes Spanish words on a whiteboard with colorful markers. Flashcards and a Spanish dictionary sit on the desk.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "knitting_scarf_pattern",
        "timestamp": "00:09:00",
        "ocr": "Easy Knitting Pattern — Beginner Scarf",
        "asr": "Craft instructor demonstrates a simple knitting pattern perfect for beginners to make their first scarf.",
        "vlm_caption": "Hands manipulate knitting needles and yarn, creating rows of stitches. A partially completed scarf hangs from the needles.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "astrophotography_milky_way",
        "timestamp": "00:14:20",
        "ocr": "Milky Way Photography — Camera Settings",
        "asr": "Photographer explains the exact camera settings and techniques needed to capture stunning photos of the Milky Way galaxy.",
        "vlm_caption": "A camera on a tripod points toward a star-filled night sky. The Milky Way stretches across the horizon above a dark landscape.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "bread_baking_sourdough",
        "timestamp": "00:11:50",
        "ocr": "Sourdough Bread Baking — Complete Guide",
        "asr": "Baker walks through the entire sourdough bread making process from starter preparation to baking in a Dutch oven.",
        "vlm_caption": "Hands shape dough on a floured surface. A scored round loaf bakes in a cast iron pot, developing a golden crust.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "hiking_gear_essentials",
        "timestamp": "00:07:30",
        "ocr": "Essential Hiking Gear for Beginners",
        "asr": "Outdoor expert reviews must-have hiking gear including boots, backpacks, and navigation tools for safe trail adventures.",
        "vlm_caption": "Hiking boots, a backpack, and a compass are laid out on a wooden table. A trail map is partially visible underneath.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "watercolor_painting_basics",
        "timestamp": "00:05:00",
        "ocr": "Watercolor Painting for Beginners",
        "asr": "Artist teaches fundamental watercolor techniques including wet-on-wet, color mixing, and brush control for beginners.",
        "vlm_caption": "A hand holds a paintbrush, applying blue watercolor to white paper. A palette with mixed colors sits nearby on an easel.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "drone_footage_editing",
        "timestamp": "00:08:15",
        "ocr": "Edit Cinematic Drone Footage",
        "asr": "Video editor shows how to color grade and edit drone footage to create cinematic aerial sequences for travel videos.",
        "vlm_caption": "A computer screen shows aerial footage of a coastline being edited in video software. Color wheels and timeline panels are visible.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "chess_opening_strategies",
        "timestamp": "00:06:45",
        "ocr": "Chess Openings — Italian Game Explained",
        "asr": "Chess coach breaks down the Italian Game opening, explaining key moves and common traps for intermediate players.",
        "vlm_caption": "A chessboard viewed from above shows pieces arranged in the Italian Game opening. A hand moves a white knight to f3.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "plant_based_diet_guide",
        "timestamp": "00:09:30",
        "ocr": "Plant-Based Diet — Complete Nutrition Guide",
        "asr": "Nutritionist explains how to get complete protein and essential nutrients on a plant-based diet without supplements.",
        "vlm_caption": "A colorful plate of vegetables, grains, and legumes is shown. A nutrition chart and food pyramid are visible in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "rock_climbing_basics",
        "timestamp": "00:07:00",
        "ocr": "Indoor Rock Climbing for Beginners",
        "asr": "Climbing instructor teaches basic techniques for indoor rock climbing including footwork, grip types, and safety procedures.",
        "vlm_caption": "A person climbs a colorful indoor rock wall with safety harness and rope. Another person belays from below on padded flooring.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "vintage_camera_collection",
        "timestamp": "00:05:20",
        "ocr": "My Vintage Film Camera Collection",
        "asr": "Photography enthusiast showcases a collection of vintage film cameras, explaining the history and unique features of each model.",
        "vlm_caption": "Various old film cameras of different sizes are displayed on wooden shelves. Some have leather cases and manual focus rings.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "calligraphy_hand_lettering",
        "timestamp": "00:04:40",
        "ocr": "Modern Calligraphy — Brush Lettering Basics",
        "asr": "Calligraphy artist demonstrates brush lettering techniques for creating beautiful handwritten quotes and designs.",
        "vlm_caption": "A hand holds a brush pen, drawing elegant cursive letters on textured paper. Ink bottles and practice sheets are nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "surfing_wave_technique",
        "timestamp": "00:08:30",
        "ocr": "Surfing Technique — How to Read Waves",
        "asr": "Professional surfer explains how to read ocean waves and position yourself correctly to catch the best rides.",
        "vlm_caption": "A surfer paddles on a board in the ocean, then stands and rides a curling wave. The beach and shoreline are visible in the distance.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "budget_travel_europe",
        "timestamp": "00:10:00",
        "ocr": "Europe on a Budget — Travel Tips",
        "asr": "Travel blogger shares money-saving tips for backpacking through Europe including hostels, cheap eats, and free attractions.",
        "vlm_caption": "A person with a backpack stands in front of a historic European building. A map and train tickets are visible in their hands.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "pottery_wheel_throwing",
        "timestamp": "00:06:15",
        "ocr": "Pottery Wheel Throwing — First Bowl",
        "asr": "Ceramics instructor demonstrates how to center clay on a pottery wheel and throw your first bowl shape.",
        "vlm_caption": "Hands shape wet clay on a spinning pottery wheel. Water splashes as the clay gradually forms a bowl shape.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "street_food_vietnam",
        "timestamp": "00:07:45",
        "ocr": "Vietnam Street Food Tour — Hanoi Old Quarter",
        "asr": "Food vlogger explores the best street food in Hanoi's Old Quarter, trying pho, banh mi, and egg coffee from local vendors.",
        "vlm_caption": "A person sits on a small plastic stool at a street food stall. A steaming bowl of noodle soup is placed in front of them.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "home_brewing_coffee",
        "timestamp": "00:05:30",
        "ocr": "Home Coffee Brewing — Pour Over Method",
        "asr": "Coffee expert demonstrates the pour over brewing method, explaining grind size, water temperature, and pouring technique.",
        "vlm_caption": "Hot water is poured from a gooseneck kettle over coffee grounds in a ceramic dripper. Fresh coffee drips into a glass carafe.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "indoor_plant_care",
        "timestamp": "00:04:00",
        "ocr": "Indoor Plant Care — Keep Them Alive",
        "asr": "Plant expert shares essential care tips for common houseplants including watering schedules, light requirements, and repotting.",
        "vlm_caption": "Various green houseplants in decorative pots sit on a windowsill. A person gently touches the leaves of a large monstera plant.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "electric_guitar_lessons",
        "timestamp": "00:08:00",
        "ocr": "Electric Guitar — First Riffs for Beginners",
        "asr": "Guitar teacher shows beginners how to play their first rock riffs on electric guitar with proper technique and timing.",
        "vlm_caption": "A person plays a black electric guitar, fingers pressing strings on the fretboard. An amplifier and pedalboard are visible behind them.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "scuba_diving_basics",
        "timestamp": "00:09:45",
        "ocr": "Scuba Diving — Open Water Certification",
        "asr": "Dive instructor explains the process of getting PADI open water certified and what to expect in your first underwater dives.",
        "vlm_caption": "A diver in full scuba gear descends into clear blue water. Colorful fish and coral reef are visible in the underwater scene.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "woodworking_shelf_diy",
        "timestamp": "00:07:20",
        "ocr": "DIY Floating Shelf — Woodworking Project",
        "asr": "Woodworker demonstrates how to build a modern floating shelf from reclaimed wood with hidden brackets.",
        "vlm_caption": "Hands use a saw to cut a wooden plank. A completed floating shelf with books and plants is mounted on a white wall.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ballet_positions_beginner",
        "timestamp": "00:05:10",
        "ocr": "Ballet for Beginners — Five Positions",
        "asr": "Ballet instructor teaches the five basic positions of ballet feet and arms for absolute beginners.",
        "vlm_caption": "A dancer in a leotard stands at a ballet barre, demonstrating first position with heels together and toes turned out.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "credit_card_rewards",
        "timestamp": "00:06:30",
        "ocr": "Best Credit Card Rewards — 2024 Guide",
        "asr": "Finance expert compares top credit card reward programs and explains how to maximize cashback and travel points.",
        "vlm_caption": "Multiple credit cards are fanned out on a desk. A laptop screen shows a comparison chart of reward rates and annual fees.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "tai_chi_morning",
        "timestamp": "00:08:00",
        "ocr": "Tai Chi Morning Routine — Flow Movements",
        "asr": "Tai chi master leads a gentle morning routine with slow flowing movements for relaxation and balance.",
        "vlm_caption": "A person performs slow martial arts movements in a park at sunrise. Trees and a calm lake are visible in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "vlogging_equipment_setup",
        "timestamp": "00:05:45",
        "ocr": "Vlogging Gear — Budget Camera Setup",
        "asr": "Content creator reviews affordable vlogging equipment including cameras, microphones, and lighting for beginners.",
        "vlm_caption": "A camera on a tripod is pointed at a ring light. A microphone and laptop are arranged on a desk for recording.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ice_cream_making",
        "timestamp": "00:06:00",
        "ocr": "Homemade Ice Cream — No Machine Recipe",
        "asr": "Chef demonstrates how to make creamy ice cream at home without an ice cream machine using simple ingredients.",
        "vlm_caption": "A person stirs a creamy mixture in a metal bowl. Scoops of vanilla ice cream are placed in a glass dish with toppings.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "mountain_biking_trails",
        "timestamp": "00:09:15",
        "ocr": "Mountain Biking — Best Beginner Trails",
        "asr": "Mountain biker recommends the best beginner-friendly trails and explains essential safety gear for off-road cycling.",
        "vlm_caption": "A cyclist rides a mountain bike down a dirt trail through a forest. Trees blur past as the bike navigates over roots and rocks.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "waterproofing_hiking_boots",
        "timestamp": "00:04:20",
        "ocr": "How to Waterproof Hiking Boots",
        "asr": "Outdoor gear expert demonstrates how to properly waterproof leather hiking boots to keep feet dry on wet trails.",
        "vlm_caption": "A person applies wax to a leather boot using a small brush. The boot is held over newspaper to catch drips.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "origami_crane_tutorial",
        "timestamp": "00:03:30",
        "ocr": "Origami Crane — Step by Step Folding",
        "asr": "Paper folding artist teaches how to make a traditional origami crane with clear step-by-step instructions.",
        "vlm_caption": "Hands fold a square piece of paper into a bird shape. A completed white paper crane sits on the table as a reference.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "stock_market_basics",
        "timestamp": "00:10:30",
        "ocr": "Stock Market for Beginners — How to Start",
        "asr": "Financial advisor explains stock market fundamentals including how to buy your first stock and build a diversified portfolio.",
        "vlm_caption": "A person points at a stock chart on a large monitor. Financial newspapers and a calculator sit on the desk.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "barista_latte_art",
        "timestamp": "00:04:00",
        "ocr": "Latte Art for Beginners — Heart Pattern",
        "asr": "Barista demonstrates how to pour a heart-shaped latte art pattern into a cup of espresso and steamed milk.",
        "vlm_caption": "A hand tilts a white cup while pouring steamed milk. A heart shape forms on the brown coffee surface.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "backpacking_southeast_asia",
        "timestamp": "00:11:00",
        "ocr": "Backpacking Southeast Asia — Route Guide",
        "asr": "Traveler shares a complete backpacking route through Southeast Asia covering Thailand, Vietnam, Cambodia, and Indonesia.",
        "vlm_caption": "A person with a large backpack stands at a train station platform. A map of Southeast Asia is visible on their phone screen.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "fermentation_kimchi",
        "timestamp": "00:06:45",
        "ocr": "How to Make Kimchi — Korean Fermentation",
        "asr": "Korean cook demonstrates traditional kimchi preparation including salting cabbage and mixing the spicy fermentation paste.",
        "vlm_caption": "Hands mix red chili paste with vegetables in a large bowl. Jars of finished kimchi are lined up on a kitchen counter.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "clay_sculpture_portrait",
        "timestamp": "00:08:30",
        "ocr": "Clay Portrait Sculpture — Sculpting Faces",
        "asr": "Sculptor demonstrates techniques for sculpting realistic human faces from clay using reference photos and proper proportions.",
        "vlm_caption": "Hands shape clay on an armature to form a human face. Sculpting tools and reference photos are arranged on the workbench.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "kayaking_river_safety",
        "timestamp": "00:07:15",
        "ocr": "Kayak Safety — River Paddling Tips",
        "asr": "Kayaking instructor covers essential safety techniques for river paddling including eddy turns and self-rescue procedures.",
        "vlm_caption": "A person in a kayak paddles through mild rapids. A helmet and life jacket are visible as they navigate around rocks.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "mechanical_keyboard_build",
        "timestamp": "00:09:30",
        "ocr": "Build a Custom Mechanical Keyboard",
        "asr": "Tech enthusiast walks through assembling a custom mechanical keyboard from parts including switches, keycaps, and PCB.",
        "vlm_caption": "Hands solder switches onto a circuit board. Colorful keycaps are being placed onto switch stems one by one.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "bird_watching_basics",
        "timestamp": "00:05:00",
        "ocr": "Bird Watching for Beginners — Essential Gear",
        "asr": "Ornithologist recommends binoculars, field guides, and apps for beginner bird watchers to identify local species.",
        "vlm_caption": "A person looks through binoculars at trees in a park. A bird identification book is open in their other hand.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "3d_printing_figurines",
        "timestamp": "00:07:45",
        "ocr": "3D Print Custom Figurines — Beginner Guide",
        "asr": "Maker explains how to 3D print custom figurines from digital models, covering slicer settings and filament choices.",
        "vlm_caption": "A 3D printer creates a small plastic figurine layer by layer. Completed colorful prints are displayed on a shelf nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "wine_tasting_technique",
        "timestamp": "00:06:00",
        "ocr": "Wine Tasting — How to Taste Like a Pro",
        "asr": "Sommelier teaches proper wine tasting technique including visual examination, aroma identification, and flavor analysis.",
        "vlm_caption": "A hand swirls red wine in a large glass. A person holds the glass to the light and then brings it to their nose.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "urban_sketching",
        "timestamp": "00:05:15",
        "ocr": "Urban Sketching — Draw City Scenes",
        "asr": "Artist demonstrates urban sketching techniques for capturing buildings, streets, and people in city environments.",
        "vlm_caption": "A person sketches a city street scene in a notebook with ink pens. Buildings and pedestrians are visible in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ferret_care_guide",
        "timestamp": "00:04:30",
        "ocr": "Pet Ferret Care — Complete Guide",
        "asr": "Veterinarian explains how to care for pet ferrets including diet, housing, and health considerations for first-time owners.",
        "vlm_caption": "A small ferret explores a multi-level cage with tubes and hammocks. The animal playfully interacts with a person's hand.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "solar_panel_installation",
        "timestamp": "00:10:00",
        "ocr": "Home Solar Panels — Installation Guide",
        "asr": "Contractor explains the process of installing residential solar panels including permits, mounting, and grid connection.",
        "vlm_caption": "Workers install solar panels on a residential roof. Blue panels are arranged in rows and wiring is visible along the edges.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ukulele_chords_beginner",
        "timestamp": "00:04:45",
        "ocr": "Ukulele Chords — First 4 Chords to Learn",
        "asr": "Music teacher shows the four essential ukulele chords for beginners and how to strum simple songs.",
        "vlm_caption": "A hand forms a C chord on a small wooden ukulele. Chord diagrams are displayed on screen as the person strums.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "beekeeping_honey_harvest",
        "timestamp": "00:08:30",
        "ocr": "Beekeeping — Harvesting Honey from Hive",
        "asr": "Beekeeper demonstrates how to safely harvest honey from a backyard beehive using proper protective equipment.",
        "vlm_caption": "A person in a white beekeeping suit opens a wooden hive box. Golden honeycomb frames are lifted out with a special tool.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "candle_making_diy",
        "timestamp": "00:05:00",
        "ocr": "DIY Scented Candles — Soy Wax Recipe",
        "asr": "Crafter shows how to make scented soy candles at home with essential oils and custom containers.",
        "vlm_caption": "Liquid wax is poured into glass jars with wicks. Finished candles with dried flowers on top cool on a wooden tray.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "frisbee_golf_course",
        "timestamp": "00:06:15",
        "ocr": "Disc Golf — Course Rules and Techniques",
        "asr": "Disc golfer explains the rules of disc golf and demonstrates throwing techniques for distance and accuracy.",
        "vlm_caption": "A person throws a flying disc toward a metal basket target in a wooded park. Trees and grass surround the course.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "tattoo_aftercare",
        "timestamp": "00:04:00",
        "ocr": "Tattoo Aftercare — Healing Guide",
        "asr": "Tattoo artist explains proper aftercare for new tattoos including washing, moisturizing, and sun protection during healing.",
        "vlm_caption": "A fresh tattoo on an arm is being gently washed with soap. A tube of aftercare ointment sits on the bathroom counter.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "rock_painting_ideas",
        "timestamp": "00:03:45",
        "ocr": "Rock Painting — Creative Designs for Kids",
        "asr": "Art teacher shows fun rock painting ideas for children using acrylic paints and simple patterns.",
        "vlm_caption": "Small smooth stones are painted with colorful designs including ladybugs, flowers, and smiley faces. Paint brushes are nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "home_security_systems",
        "timestamp": "00:07:30",
        "ocr": "Home Security — Best DIY Systems 2024",
        "asr": "Security expert reviews top DIY home security systems including cameras, sensors, and smart doorbells for home protection.",
        "vlm_caption": "A smart doorbell camera is mounted next to a front door. A phone screen shows a live video feed of the porch area.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "roller_skating_basics",
        "timestamp": "00:05:30",
        "ocr": "Roller Skating for Beginners — First Steps",
        "asr": "Skating instructor teaches basic roller skating techniques including balance, stopping, and turning for absolute beginners.",
        "vlm_caption": "A person wearing roller skates holds onto a railing while practicing balance. Protective knee and elbow pads are visible.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "succulent_arrangement",
        "timestamp": "00:04:15",
        "ocr": "Succulent Arrangement — DIY Planter Design",
        "asr": "Gardener demonstrates how to arrange different succulent varieties in a decorative planter for indoor display.",
        "vlm_caption": "Small succulent plants of various shapes and colors are arranged in a shallow ceramic dish. Decorative stones fill the gaps.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "voice_acting_basics",
        "timestamp": "00:06:00",
        "ocr": "Voice Acting — Beginner Techniques",
        "asr": "Voice actor shares fundamental techniques for voice acting including breathing, projection, and character voices.",
        "vlm_caption": "A person speaks into a professional microphone in a soundproof booth. A script is held in one hand as they perform.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "kite_flying_tips",
        "timestamp": "00:04:30",
        "ocr": "Kite Flying — Get Your Kite in the Air",
        "asr": "Kite enthusiast explains how to launch and control a kite including wind conditions and line handling techniques.",
        "vlm_caption": "A colorful kite soars high in a blue sky. A person on a grassy field holds the string and looks up at the flying kite.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "leather_crafting_wallet",
        "timestamp": "00:07:00",
        "ocr": "Leather Crafting — Make a Simple Wallet",
        "asr": "Leatherworker demonstrates how to cut, stitch, and finish a handmade leather wallet from a pattern.",
        "vlm_caption": "Hands punch holes in a piece of brown leather. A needle and thread are used to stitch two pieces together.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "aquarium_setup_freshwater",
        "timestamp": "00:08:15",
        "ocr": "Freshwater Aquarium Setup — Complete Guide",
        "asr": "Aquarist explains how to set up a freshwater aquarium including tank cycling, filtration, and fish selection for beginners.",
        "vlm_caption": "A glass aquarium with gravel, plants, and decorations is being filled with water. Colorful fish swim inside the completed tank.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "juggling_three_balls",
        "timestamp": "00:03:30",
        "ocr": "Juggling — Learn 3 Balls in 10 Minutes",
        "asr": "Juggler teaches the cascade pattern for three balls with step-by-step instructions for beginners.",
        "vlm_caption": "Three colorful balls arc through the air in a continuous pattern. A person's hands move rhythmically to catch and throw them.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "podcast_equipment_setup",
        "timestamp": "00:06:30",
        "ocr": "Podcast Setup — Budget Equipment Guide",
        "asr": "Podcaster reviews affordable microphones, headphones, and recording software for starting a podcast from home.",
        "vlm_caption": "A microphone on a boom arm is positioned in front of a laptop. Headphones hang on a stand nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "stamp_collecting_guide",
        "timestamp": "00:05:00",
        "ocr": "Stamp Collecting — Beginner's Guide",
        "asr": "Philatelist explains how to start a stamp collection including storage, identification, and valuing rare stamps.",
        "vlm_caption": "A magnifying glass is held over colorful postage stamps arranged in a protective album page.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "paragliding_first_flight",
        "timestamp": "00:09:00",
        "ocr": "Paragliding — First Tandem Flight Experience",
        "asr": "Paragliding instructor describes what to expect on your first tandem flight including takeoff, landing, and safety.",
        "vlm_caption": "Two people are strapped together under a large colorful paraglider wing. They run off a grassy hilltop and soar into the sky.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "soap_making_cold_process",
        "timestamp": "00:07:45",
        "ocr": "Cold Process Soap Making — Complete Tutorial",
        "asr": "Soap maker demonstrates the cold process method for making handmade soap from oils and lye with safety precautions.",
        "vlm_caption": "Liquid soap mixture is poured into a wooden mold. Bars of cured soap with swirled colors are displayed on a rack.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "trail_running_tips",
        "timestamp": "00:06:30",
        "ocr": "Trail Running — Techniques for Beginners",
        "asr": "Trail runner shares techniques for running on uneven terrain including foot placement, pacing, and downhill form.",
        "vlm_caption": "A runner navigates a narrow dirt trail through a forest. Roots and rocks are visible on the uneven path.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "whittling_wood_basics",
        "timestamp": "00:05:15",
        "ocr": "Whittling — First Wood Carving Project",
        "asr": "Woodworker teaches basic whittling techniques and safety while carving a simple wooden spoon from a block.",
        "vlm_caption": "Hands hold a small knife and carefully shave thin curls from a piece of wood. Wood shavings collect on a workbench.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "virtual_reality_gaming",
        "timestamp": "00:08:00",
        "ocr": "VR Gaming — Best Headsets for Beginners",
        "asr": "Tech reviewer compares virtual reality headsets for gaming including resolution, comfort, and game library options.",
        "vlm_caption": "A person wears a VR headset and holds motion controllers while moving their arms in a virtual environment.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "bonsai_tree_care",
        "timestamp": "00:06:45",
        "ocr": "Bonsai Tree Care — Pruning and Wiring",
        "asr": "Bonsai artist demonstrates pruning, wiring, and repotting techniques for maintaining miniature trees.",
        "vlm_caption": "Small scissors trim the branches of a tiny tree in a shallow pot. Copper wire wraps around branches to shape them.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "drone_photography_tips",
        "timestamp": "00:07:30",
        "ocr": "Drone Photography — Composition Techniques",
        "asr": "Drone pilot shares aerial photography composition tips including leading lines, symmetry, and golden hour timing.",
        "vlm_caption": "A drone hovers above a landscape capturing a photo. The controller screen shows a live aerial view of a coastline.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "embroidery_stitches",
        "timestamp": "00:05:00",
        "ocr": "Embroidery Stitches — Beginner Sampler",
        "asr": "Embroiderer teaches five basic embroidery stitches including backstitch, satin stitch, and French knots.",
        "vlm_caption": "A hand pulls colored thread through fabric in a wooden hoop. Various stitch patterns are visible on a white cloth.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "fossil_hunting_guide",
        "timestamp": "00:07:15",
        "ocr": "Fossil Hunting — Where to Find Ancient Remains",
        "asr": "Paleontologist explains where and how to find fossils including tools, locations, and identification techniques for beginners.",
        "vlm_caption": "A person uses a small hammer to chip at rock layers in a cliff face. Fossil fragments are visible in the sediment.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "glass_blowing_demo",
        "timestamp": "00:08:45",
        "ocr": "Glass Blowing — Watch Art Being Made",
        "asr": "Glass artist demonstrates the ancient art of glass blowing, shaping molten glass with tools and breath.",
        "vlm_caption": "A glowing orange blob of molten glass rotates on a metal rod. The artist shapes it with wooden tools near a furnace.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "hammock_camping_setup",
        "timestamp": "00:05:30",
        "ocr": "Hammock Camping — Complete Setup Guide",
        "asr": "Outdoor enthusiast demonstrates how to set up a camping hammock with tarp and bug net for comfortable wilderness sleep.",
        "vlm_caption": "A hammock is suspended between two trees in a forest. A tarp is pitched above it and a sleeping bag is inside.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ice_hockey_skills",
        "timestamp": "00:06:00",
        "ocr": "Ice Hockey — Basic Skating Skills",
        "asr": "Hockey coach teaches fundamental ice skating skills including forward stride, stopping, and backward skating.",
        "vlm_caption": "A person skates on an ice rink wearing hockey gear. They practice stopping by turning their skates sideways.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "jewelry_making_earrings",
        "timestamp": "00:04:30",
        "ocr": "DIY Earrings — Wire Wrapping Tutorial",
        "asr": "Jewelry maker demonstrates wire wrapping techniques to create custom earrings with beads and gemstones.",
        "vlm_caption": "Hands twist thin wire around beads using pliers. Finished dangling earrings hang from a display stand.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "kombucha_brewing",
        "timestamp": "00:06:15",
        "ocr": "Kombucha Brewing — First Batch Guide",
        "asr": "Fermentation enthusiast explains how to brew kombucha at home including the SCOBY, sweet tea, and bottling process.",
        "vlm_caption": "A glass jar with a rubber band and cloth cover sits on a counter. Bubbles rise in the amber liquid inside.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "laser_tag_strategy",
        "timestamp": "00:04:00",
        "ocr": "Laser Tag — Winning Strategies",
        "asr": "Laser tag player shares team strategies and individual tactics for dominating in arena laser tag matches.",
        "vlm_caption": "Players in dark vests with glowing targets run through a dimly lit arena with neon walls and obstacles.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "metal_detecting_beach",
        "timestamp": "00:06:30",
        "ocr": "Metal Detecting — Beach Treasure Hunting",
        "asr": "Treasure hunter demonstrates metal detecting on a beach and explains how to identify valuable finds from trash.",
        "vlm_caption": "A person sweeps a metal detector coil over wet sand. They dig into the sand with a small shovel and pull out a coin.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "nail_art_designs",
        "timestamp": "00:05:00",
        "ocr": "Nail Art — Easy Designs for Beginners",
        "asr": "Nail technician demonstrates simple nail art designs including polka dots, stripes, and floral patterns using basic tools.",
        "vlm_caption": "A hand with painted nails is shown close-up. A thin brush applies white dots over a pink base coat.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "orienteering_compass",
        "timestamp": "00:05:45",
        "ocr": "Orienteering — Map and Compass Navigation",
        "asr": "Orienteering instructor teaches how to use a compass with a topographic map for wilderness navigation.",
        "vlm_caption": "A person holds a compass over a detailed map. They align the compass needle with map markings in a forest setting.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "parkour_training",
        "timestamp": "00:06:00",
        "ocr": "Parkour Training — Beginner Moves",
        "asr": "Parkour coach teaches basic parkour movements including rolls, vaults, and precision jumps for beginners.",
        "vlm_caption": "An athlete runs and vaults over a concrete wall in an urban environment. They roll on the ground and continue running.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "quilting_patterns",
        "timestamp": "00:07:00",
        "ocr": "Quilting — First Quilt Pattern Tutorial",
        "asr": "Quilter demonstrates how to piece together fabric squares and quilt layers to make a simple patchwork blanket.",
        "vlm_caption": "Colorful fabric squares are arranged in a grid pattern. A sewing machine stitches the pieces together on a large table.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "robotics_arduino_project",
        "timestamp": "00:08:30",
        "ocr": "Arduino Robot — Build Your First Robot",
        "asr": "Engineer demonstrates how to build a simple robot using Arduino, motors, sensors, and basic programming.",
        "vlm_caption": "A small robot with wheels moves across a table. Wires connect to an Arduino board and a breadboard with components.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "salsa_dancing_steps",
        "timestamp": "00:05:15",
        "ocr": "Salsa Dancing — Basic Steps for Beginners",
        "asr": "Dance instructor teaches the basic salsa step pattern and partner turns for absolute beginners.",
        "vlm_caption": "A couple dances salsa in a studio with mirrors. The man leads the woman through a turn while stepping to the rhythm.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "taxidermy_basics",
        "timestamp": "00:07:30",
        "ocr": "Taxidermy — Bird Mounting Basics",
        "asr": "Taxidermist demonstrates the process of mounting a bird specimen including skinning, preserving, and posing.",
        "vlm_caption": "A person works on a bird specimen on a workbench. Feathers, tools, and reference photos are arranged nearby.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "underwater_photography",
        "timestamp": "00:08:00",
        "ocr": "Underwater Photography — Beginner Tips",
        "asr": "Underwater photographer shares tips for capturing marine life including lighting, composition, and camera housing.",
        "vlm_caption": "A diver with a camera takes photos of colorful coral reef. Fish swim around the photographer in clear blue water.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ventriloquism_basics",
        "timestamp": "00:05:00",
        "ocr": "Ventriloquism — Learn to Throw Your Voice",
        "asr": "Ventriloquist teaches basic voice throwing techniques and puppet manipulation for beginners.",
        "vlm_caption": "A performer sits with a puppet on their knee. The puppet's mouth moves while the performer speaks without moving their lips.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "windsurfing_basics",
        "timestamp": "00:06:30",
        "ocr": "Windsurfing — First Time on the Board",
        "asr": "Windsurfing instructor teaches how to stand on the board, hold the sail, and catch wind for beginners.",
        "vlm_caption": "A person stands on a board with a sail, balancing on choppy water. They grip the boom and lean back against the wind.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "xylophone_playing",
        "timestamp": "00:04:00",
        "ocr": "Xylophone — First Songs for Beginners",
        "asr": "Music teacher shows how to play simple songs on a xylophone using mallets and reading basic notation.",
        "vlm_caption": "A child strikes colorful bars on a xylophone with two mallets. Musical notes are displayed above the instrument.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "yoga_wheel_pose",
        "timestamp": "00:05:30",
        "ocr": "Yoga Wheel Pose — Backbend Tutorial",
        "asr": "Yoga instructor demonstrates how to safely perform wheel pose including warm-up stretches and modifications.",
        "vlm_caption": "A person arches backward into a deep backbend on a yoga mat. Their hands and feet press into the mat in a bridge position.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "zumba_fitness_class",
        "timestamp": "00:06:00",
        "ocr": "Zumba Fitness — Dance Workout Class",
        "asr": "Zumba instructor leads a high-energy dance fitness class with Latin-inspired moves and upbeat music.",
        "vlm_caption": "A group of people dance in a fitness studio following an instructor. They move their hips and arms to fast-paced music.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "archery_target_practice",
        "timestamp": "00:05:15",
        "ocr": "Archery — Target Practice for Beginners",
        "asr": "Archery coach teaches proper stance, draw technique, and aiming for hitting the target consistently.",
        "vlm_caption": "A person draws a bow and releases an arrow toward a circular target. The arrow hits the outer ring of the target.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "billiards_technique",
        "timestamp": "00:06:00",
        "ocr": "Billiards — Cue Ball Control Techniques",
        "asr": "Pool player explains cue ball control including spin, speed, and angle for setting up your next shot.",
        "vlm_caption": "A cue strikes a white ball on a green felt table. The ball rolls and hits a colored ball, sending it into a pocket.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "crocheting_amigurumi",
        "timestamp": "00:05:30",
        "ocr": "Amigurumi Crochet — Cute Plush Toys",
        "asr": "Crocheter demonstrates how to make small stuffed animals using amigurumi techniques and basic stitches.",
        "vlm_caption": "Hands crochet a small round shape with colorful yarn. Completed plush animals sit on a shelf in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "darts_throwing_tips",
        "timestamp": "00:04:00",
        "ocr": "Darts — How to Throw Accurately",
        "asr": "Darts player explains grip, stance, and throwing technique for consistently hitting the triple 20 and bullseye.",
        "vlm_caption": "A hand holds three darts and throws one toward a dartboard. The dart lands in the triple 20 section.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "equestrian_riding_basics",
        "timestamp": "00:07:00",
        "ocr": "Horseback Riding — First Lesson Guide",
        "asr": "Riding instructor teaches basic horseback riding including mounting, posture, and controlling the horse at a walk.",
        "vlm_caption": "A person sits upright on a horse in an outdoor arena. An instructor holds the reins and guides the horse.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "fencing_foil_technique",
        "timestamp": "00:06:30",
        "ocr": "Fencing — Foil Technique for Beginners",
        "asr": "Fencing coach demonstrates basic foil techniques including en garde stance, lunge, and parry for beginners.",
        "vlm_caption": "Two fencers in white protective gear face each other on a strip. One lunges forward with a foil extended.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "go_kart_racing",
        "timestamp": "00:05:00",
        "ocr": "Go Kart Racing — Track Day Experience",
        "asr": "Racing enthusiast shares go kart racing tips including racing lines, overtaking, and braking points on the track.",
        "vlm_caption": "Small racing karts speed around an indoor track with barriers. Drivers wear helmets and racing suits.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "hula_hoop_tricks",
        "timestamp": "00:04:00",
        "ocr": "Hula Hoop — Beginner Tricks Tutorial",
        "asr": "Hoop dancer teaches basic hula hoop tricks including waist hooping, hand spins, and off-body moves.",
        "vlm_caption": "A person spins a colorful hoop around their waist. They then toss it into the air and catch it on their arm.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "inline_skating_tricks",
        "timestamp": "00:05:30",
        "ocr": "Inline Skating — Basic Tricks for Beginners",
        "asr": "Skater demonstrates basic inline skating tricks including crossovers, jumps, and grinds for beginners.",
        "vlm_caption": "A person on inline skates glides along a concrete path. They jump over a small obstacle and land smoothly.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "judo_throws_beginner",
        "timestamp": "00:06:00",
        "ocr": "Judo — Basic Throws for Beginners",
        "asr": "Judo instructor demonstrates basic throws including osoto gari and ippon seoi nage with proper breakfall technique.",
        "vlm_caption": "Two people in white judo uniforms practice a throw on a padded mat. One person is thrown and rolls on the mat.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "karate_kata_practice",
        "timestamp": "00:05:30",
        "ocr": "Karate — First Kata Practice",
        "asr": "Karate instructor teaches the first kata form including stances, blocks, punches, and kicks in sequence.",
        "vlm_caption": "A person in a white karate gi performs a series of punches and blocks in a dojo. They bow at the beginning and end.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "luge_winter_sport",
        "timestamp": "00:07:00",
        "ocr": "Luge — Winter Sliding Sport Explained",
        "asr": "Luge athlete explains the sport including the sled, track, body position, and steering technique for high-speed runs.",
        "vlm_caption": "An athlete lies on a small sled and slides feet-first down an icy track. They steer with subtle leg movements.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "miniature_painting",
        "timestamp": "00:05:00",
        "ocr": "Miniature Painting — Warhammer Figures",
        "asr": "Painter demonstrates techniques for painting detailed miniature figures including base coats, washes, and highlights.",
        "vlm_caption": "A hand holds a tiny brush and paints a small plastic figure. Paint pots and a magnifying lamp are on the desk.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "nunchaku_training",
        "timestamp": "00:04:30",
        "ocr": "Nunchaku — Basic Techniques and Safety",
        "asr": "Martial artist demonstrates basic nunchaku techniques including figure-eight patterns and wrist rolls with safety tips.",
        "vlm_caption": "A person spins two connected sticks in a figure-eight pattern. They perform wrist rolls and catches in a dojo.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "obstacle_course_racing",
        "timestamp": "00:06:30",
        "ocr": "OCR Training — Obstacle Course Race Prep",
        "asr": "Athlete trains for obstacle course races including rope climbs, wall jumps, and monkey bars with strength exercises.",
        "vlm_caption": "A person climbs a rope in a gym. They then jump over a wall and swing across monkey bars in a training course.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "paddleboarding_basics",
        "timestamp": "00:05:00",
        "ocr": "Paddleboarding — First Time on the Water",
        "asr": "Instructor teaches how to stand up on a paddleboard, hold the paddle, and maintain balance on calm water.",
        "vlm_caption": "A person stands on a wide board and paddles across calm water. Mountains and trees are visible in the background.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "quidditch_real_sport",
        "timestamp": "00:06:00",
        "ocr": "Quidditch — Real Life Muggle Sport",
        "asr": "Quidditch player explains the real-world sport based on Harry Potter including rules, positions, and gameplay.",
        "vlm_caption": "Players run on a field with brooms between their legs. One player throws a ball through hoops while others tackle.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "rugby_basics",
        "timestamp": "00:06:30",
        "ocr": "Rugby — Basic Rules and Gameplay",
        "asr": "Rugby player explains basic rules including passing backward, tackling, scoring tries, and conversion kicks.",
        "vlm_caption": "Players in striped jerseys tackle each other on a grass field. One player runs with the ball toward the goal line.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "slacklining_park",
        "timestamp": "00:04:30",
        "ocr": "Slacklining — Balance on a Tight Rope",
        "asr": "Slackliner demonstrates how to balance and walk on a slackline tied between two trees in a park.",
        "vlm_caption": "A person balances on a flat webbing stretched between trees. They use their arms for balance and take careful steps.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "taekwondo_kicks",
        "timestamp": "00:05:30",
        "ocr": "Taekwondo — Basic Kicking Techniques",
        "asr": "Taekwondo instructor demonstrates basic kicks including front kick, roundhouse kick, and side kick with proper form.",
        "vlm_caption": "A person in a white uniform with a black belt performs a high kick. They strike a padded target held by a partner.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ultimate_frisbee",
        "timestamp": "00:05:00",
        "ocr": "Ultimate Frisbee — Rules and Gameplay",
        "asr": "Ultimate player explains the rules of ultimate frisbee including passing, scoring, and the spirit of the game.",
        "vlm_caption": "Players throw a flying disc on a grass field. One player catches the disc in the end zone and teammates celebrate.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "volleyball_spiking",
        "timestamp": "00:05:30",
        "ocr": "Volleyball — How to Spike a Volleyball",
        "asr": "Volleyball coach teaches spiking technique including approach, jump, arm swing, and contact point for powerful attacks.",
        "vlm_caption": "A player jumps high and strikes a volleyball over the net. The ball travels fast toward the opposing team's court.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "wakeboarding_tricks",
        "timestamp": "00:06:00",
        "ocr": "Wakeboarding — First Tricks on the Water",
        "asr": "Wakeboarder teaches beginner tricks including surface 180s, ollies, and grabs while being towed by a boat.",
        "vlm_caption": "A person on a wakeboard jumps over the wake of a boat. They grab the board mid-air and land back on the water.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "x_country_skiing",
        "timestamp": "00:06:30",
        "ocr": "Cross Country Skiing — Classic Technique",
        "asr": "Ski instructor teaches classic cross country skiing technique including diagonal stride, double poling, and herringbone.",
        "vlm_caption": "A skier glides along a groomed trail through a snowy forest. They use poles to push forward in a rhythmic motion.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "yoyo_tricks",
        "timestamp": "00:04:00",
        "ocr": "Yo-Yo Tricks — Beginner to Intermediate",
        "asr": "Yo-yo champion demonstrates tricks including sleeper, walk the dog, rock the baby, and more advanced string tricks.",
        "vlm_caption": "A hand performs yo-yo tricks. The yo-yo sleeps at the end of the string and returns to the hand smoothly.",
        "label": 0,
        "negative_type": "distractor"
    },
    {
        "video_id": "ziplining_adventure",
        "timestamp": "00:05:00",
        "ocr": "Ziplining — First Canopy Tour Experience",
        "asr": "Adventure guide explains ziplining safety and what to expect on your first canopy tour through the treetops.",
        "vlm_caption": "A person wearing a harness slides along a cable high above the forest floor. Trees rush by as they descend.",
        "label": 0,
        "negative_type": "distractor"
    }
]

def load_original_dataset(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def create_global_pool_dataset(original: dict, distractors: list, pool_size: int = 100) -> dict:
    """
    Tạo dataset mới với global pool.
    
    Mỗi query search trong pool chung gồm:
    - Tất cả candidates từ tất cả queries (~45 items)
    - Random distractors để đạt pool_size (~100 items)
    """
    # Collect all original candidates
    all_original_candidates = []
    for q in original["queries"]:
        for c in q["candidates"]:
            all_original_candidates.append(c)
    
    # Remove duplicates by video_id
    seen = set()
    unique_candidates = []
    for c in all_original_candidates:
        if c["video_id"] not in seen:
            seen.add(c["video_id"])
            unique_candidates.append(c)
    
    # Build global pool
    global_pool = unique_candidates.copy()
    
    # Add distractors until reach pool_size
    random.shuffle(distractors)
    needed = max(0, pool_size - len(global_pool))
    selected_distractors = distractors[:needed]
    global_pool.extend(selected_distractors)
    
    # Shuffle pool
    random.shuffle(global_pool)
    
    # Build new queries: each query has ALL pool items, with correct label
    new_queries = []
    for q in original["queries"]:
        # Find which candidate is positive for this query
        positive_video_ids = {
            c["video_id"] 
            for c in q["candidates"] 
            if c["label"] == 1
        }
        
        new_candidates = []
        for c in global_pool:
            new_c = copy.deepcopy(c)
            new_c["label"] = 1 if c["video_id"] in positive_video_ids else 0
            # Reset negative_type for distractors
            if new_c["label"] == 0 and c.get("negative_type") == "distractor":
                new_c["negative_type"] = "distractor"
            elif new_c["label"] == 0:
                # Try to infer negative type from original
                new_c["negative_type"] = "hard_negative"
            else:
                new_c["negative_type"] = "positive"
            new_candidates.append(new_c)
        
        new_queries.append({
            "query_id": q["query_id"],
            "query": q["query"],
            "candidates": new_candidates
        })
    
    return {
        "version": "3.0-global-pool",
        "description": "Global pool benchmark with distractors. Each query searches in a shared pool of ~100 items.",
        "total_queries": len(new_queries),
        "pool_size": len(global_pool),
        "negative_type_taxonomy": original["negative_type_taxonomy"] + ["distractor", "hard_negative"],
        "queries": new_queries
    }

def main():
    # Load original
    original = load_original_dataset("data/benchmark_dataset.json")
    
    # Create global pool version
    new_dataset = create_global_pool_dataset(original, DISTRACTORS, pool_size=100)
    
    # Save
    out_path = "data/benchmark_dataset_global_pool.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_dataset, f, indent=2, ensure_ascii=False)
    
    print(f"Created global pool dataset:")
    print(f"  Queries: {new_dataset['total_queries']}")
    print(f"  Pool size: {new_dataset['pool_size']}")
    print(f"  Total candidates per query: {len(new_dataset['queries'][0]['candidates'])}")
    print(f"  Saved to: {out_path}")

if __name__ == "__main__":
    main()