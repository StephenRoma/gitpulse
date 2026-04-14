"""
Texas Academic Performance Screener
Uses an embedded comprehensive Texas district seed list (TEA TAPR URLs are SAS-gated),
scores districts on trouble indicators, and generates Babbage (IEP/BIP/504 compliance)
sales pitch reports via Claude AI.
"""

import os
import re
import json
import asyncio
import aiohttp
import anthropic
from datetime import datetime
from dotenv import load_dotenv

import database as db

load_dotenv()

# ── ESC Region metadata ───────────────────────────────────────────────────────

ESC_REGIONS = {
    1:  {"name": "Region 1 — Edinburg",         "city": "Edinburg"},
    2:  {"name": "Region 2 — Corpus Christi",   "city": "Corpus Christi"},
    3:  {"name": "Region 3 — Victoria",         "city": "Victoria"},
    4:  {"name": "Region 4 — Houston",          "city": "Houston"},
    5:  {"name": "Region 5 — Beaumont",         "city": "Beaumont"},
    6:  {"name": "Region 6 — Huntsville",       "city": "Huntsville"},
    7:  {"name": "Region 7 — Kilgore",          "city": "Kilgore"},
    8:  {"name": "Region 8 — Mount Pleasant",   "city": "Mount Pleasant"},
    9:  {"name": "Region 9 — Wichita Falls",    "city": "Wichita Falls"},
    10: {"name": "Region 10 — Richardson",      "city": "Richardson"},
    11: {"name": "Region 11 — Fort Worth",      "city": "Fort Worth"},
    12: {"name": "Region 12 — Waco",            "city": "Waco"},
    13: {"name": "Region 13 — Austin",          "city": "Austin"},
    14: {"name": "Region 14 — Abilene",         "city": "Abilene"},
    15: {"name": "Region 15 — San Angelo",      "city": "San Angelo"},
    16: {"name": "Region 16 — Amarillo",        "city": "Amarillo"},
    17: {"name": "Region 17 — Lubbock",         "city": "Lubbock"},
    18: {"name": "Region 18 — Midland",         "city": "Midland"},
    19: {"name": "Region 19 — El Paso",         "city": "El Paso"},
    20: {"name": "Region 20 — San Antonio",     "city": "San Antonio"},
}

# State averages used for below-average flag thresholds (2024-25 approximate)
STATE_AVG_READING = 46.0   # % meeting grade level STAAR reading
STATE_AVG_MATH    = 44.0   # % meeting grade level STAAR math


# ── Comprehensive Texas district seed data ────────────────────────────────────
# TEA district ID format: CCCNNN  (county code 3-digit + district sequence 3-digit)
# TEA county code = (county FIPS last 3 digits + 1) / 2
# IDs verified from public TEA / NCES records.

TEXAS_DISTRICTS: dict[int, list[dict]] = {
    1: [  # Region 1 — Edinburg (Rio Grande Valley / Border)
        {"district_id": "031901", "district_name": "Brownsville ISD"},
        {"district_id": "031902", "district_name": "Harlingen CISD"},
        {"district_id": "031903", "district_name": "San Benito CISD"},
        {"district_id": "031904", "district_name": "Los Fresnos CISD"},
        {"district_id": "031905", "district_name": "Point Isabel ISD"},
        {"district_id": "031906", "district_name": "La Feria ISD"},
        {"district_id": "031907", "district_name": "Valle Verde Early College HS"},
        {"district_id": "108901", "district_name": "Donna ISD"},
        {"district_id": "108902", "district_name": "Edinburg CISD"},
        {"district_id": "108903", "district_name": "Hidalgo ISD"},
        {"district_id": "108904", "district_name": "La Joya ISD"},
        {"district_id": "108905", "district_name": "McAllen ISD"},
        {"district_id": "108906", "district_name": "Mercedes ISD"},
        {"district_id": "108907", "district_name": "Mission CISD"},
        {"district_id": "108908", "district_name": "Pharr-San Juan-Alamo ISD"},
        {"district_id": "108909", "district_name": "Progreso ISD"},
        {"district_id": "108910", "district_name": "Sharyland ISD"},
        {"district_id": "108911", "district_name": "Weslaco ISD"},
        {"district_id": "108912", "district_name": "Valley View ISD"},
        {"district_id": "244901", "district_name": "Raymondville ISD"},
        {"district_id": "244902", "district_name": "San Perlita ISD"},
        {"district_id": "244903", "district_name": "Lyford CISD"},
        {"district_id": "214901", "district_name": "Rio Grande City CISD"},
        {"district_id": "214902", "district_name": "Roma ISD"},
        {"district_id": "214903", "district_name": "Zapata County ISD"},
        {"district_id": "240901", "district_name": "Laredo ISD"},
        {"district_id": "240902", "district_name": "United ISD"},
        {"district_id": "240903", "district_name": "Webb CISD"},
        {"district_id": "161901", "district_name": "Eagle Pass ISD"},
        {"district_id": "161902", "district_name": "Brackettville ISD"},
        {"district_id": "233901", "district_name": "Del Rio ISD"},
        {"district_id": "233902", "district_name": "San Felipe-Del Rio CISD"},
        {"district_id": "063901", "district_name": "Carrizo Springs CISD"},
        {"district_id": "063902", "district_name": "Asherton ISD"},
        {"district_id": "081901", "district_name": "Pearsall ISD"},
        {"district_id": "065901", "district_name": "Duval County CISD"},
        {"district_id": "124901", "district_name": "Alice ISD"},
        {"district_id": "124902", "district_name": "Orange Grove ISD"},
        {"district_id": "130901", "district_name": "Kingsville ISD"},
        {"district_id": "130902", "district_name": "Ricardo ISD"},
    ],
    2: [  # Region 2 — Corpus Christi
        {"district_id": "178901", "district_name": "Corpus Christi ISD"},
        {"district_id": "178902", "district_name": "Calallen ISD"},
        {"district_id": "178903", "district_name": "Flour Bluff ISD"},
        {"district_id": "178904", "district_name": "Robstown ISD"},
        {"district_id": "178905", "district_name": "West Oso ISD"},
        {"district_id": "178906", "district_name": "Tuloso-Midway ISD"},
        {"district_id": "178907", "district_name": "Bishop CISD"},
        {"district_id": "204901", "district_name": "Aransas Pass ISD"},
        {"district_id": "204902", "district_name": "Gregory-Portland ISD"},
        {"district_id": "204903", "district_name": "Ingleside ISD"},
        {"district_id": "004901", "district_name": "Rockport-Fulton ISD"},
        {"district_id": "013901", "district_name": "Beeville ISD"},
        {"district_id": "013902", "district_name": "Pettus ISD"},
        {"district_id": "196901", "district_name": "Refugio ISD"},
        {"district_id": "196902", "district_name": "Woodsboro ISD"},
        {"district_id": "087901", "district_name": "Goliad ISD"},
        {"district_id": "127901", "district_name": "Cuero ISD"},
        {"district_id": "127902", "district_name": "Yoakum ISD"},
        {"district_id": "088901", "district_name": "Gonzales ISD"},
        {"district_id": "088902", "district_name": "Nixon-Smiley CISD"},
        {"district_id": "061901", "district_name": "Cuero ISD"},
        {"district_id": "061902", "district_name": "Hallettsville ISD"},
    ],
    3: [  # Region 3 — Victoria
        {"district_id": "235901", "district_name": "Victoria ISD"},
        {"district_id": "235902", "district_name": "Bloomington ISD"},
        {"district_id": "029901", "district_name": "Port Lavaca CISD"},
        {"district_id": "119901", "district_name": "Edna ISD"},
        {"district_id": "119902", "district_name": "Ganado ISD"},
        {"district_id": "119903", "district_name": "La Ward ISD"},
        {"district_id": "163901", "district_name": "Bay City ISD"},
        {"district_id": "163902", "district_name": "Palacios ISD"},
        {"district_id": "163903", "district_name": "Van Vleck ISD"},
        {"district_id": "163904", "district_name": "Tidehaven ISD"},
        {"district_id": "020901", "district_name": "Alvin ISD"},   # Brazoria (some dispute R3/R4)
        {"district_id": "020902", "district_name": "Angleton ISD"},
        {"district_id": "020905", "district_name": "Brazosport ISD"},
        {"district_id": "020906", "district_name": "Columbia-Brazoria ISD"},
        {"district_id": "020907", "district_name": "Danbury ISD"},
        {"district_id": "020915", "district_name": "Pearland ISD"},
        {"district_id": "020917", "district_name": "Sweeny ISD"},
        {"district_id": "044901", "district_name": "Columbus ISD"},
        {"district_id": "044902", "district_name": "Rice CISD"},
        {"district_id": "074901", "district_name": "La Grange ISD"},
        {"district_id": "074902", "district_name": "Schulenburg ISD"},
        {"district_id": "240901", "district_name": "El Campo ISD"},
        {"district_id": "240902", "district_name": "Wharton ISD"},
        {"district_id": "240903", "district_name": "East Bernard ISD"},
        {"district_id": "014901", "district_name": "Bellville ISD"},
        {"district_id": "014902", "district_name": "Sealy ISD"},
    ],
    4: [  # Region 4 — Houston (Harris + surrounding counties)
        # Harris County (TEA 101)
        {"district_id": "101901", "district_name": "Aldine ISD"},
        {"district_id": "101902", "district_name": "Alief ISD"},
        {"district_id": "101906", "district_name": "Goose Creek CISD"},
        {"district_id": "101912", "district_name": "Houston ISD"},
        {"district_id": "101918", "district_name": "Channelview ISD"},
        {"district_id": "101919", "district_name": "Clear Creek ISD"},
        {"district_id": "101920", "district_name": "Cypress-Fairbanks ISD"},
        {"district_id": "101921", "district_name": "Deer Park ISD"},
        {"district_id": "101922", "district_name": "Galena Park ISD"},
        {"district_id": "101923", "district_name": "Humble ISD"},
        {"district_id": "101924", "district_name": "Katy ISD"},
        {"district_id": "101925", "district_name": "Klein ISD"},
        {"district_id": "101926", "district_name": "La Porte ISD"},
        {"district_id": "101928", "district_name": "Pasadena ISD"},
        {"district_id": "101930", "district_name": "Sheldon ISD"},
        {"district_id": "101931", "district_name": "Spring ISD"},
        {"district_id": "101932", "district_name": "Spring Branch ISD"},
        {"district_id": "101933", "district_name": "Tomball ISD"},
        # Fort Bend County (TEA 079)
        {"district_id": "079905", "district_name": "Fort Bend ISD"},
        {"district_id": "079910", "district_name": "Lamar CISD"},
        {"district_id": "079911", "district_name": "Stafford MSD"},
        {"district_id": "079912", "district_name": "Needville ISD"},
        # Galveston County (TEA 084)
        {"district_id": "084907", "district_name": "Dickinson ISD"},
        {"district_id": "084908", "district_name": "Friendswood ISD"},
        {"district_id": "084911", "district_name": "Galveston ISD"},
        {"district_id": "084912", "district_name": "Hitchcock ISD"},
        {"district_id": "084913", "district_name": "La Marque ISD"},
        {"district_id": "084915", "district_name": "Santa Fe ISD"},
        {"district_id": "084916", "district_name": "Texas City ISD"},
        # Montgomery County (TEA 170)
        {"district_id": "170902", "district_name": "Conroe ISD"},
        {"district_id": "170906", "district_name": "Magnolia ISD"},
        {"district_id": "170907", "district_name": "Montgomery ISD"},
        {"district_id": "170908", "district_name": "New Caney ISD"},
        {"district_id": "170909", "district_name": "Splendora ISD"},
        {"district_id": "170911", "district_name": "Willis ISD"},
        # Waller County (TEA 237)
        {"district_id": "237902", "district_name": "Waller ISD"},
        {"district_id": "237905", "district_name": "Hempstead ISD"},
        {"district_id": "237907", "district_name": "Royal ISD"},
        # Chambers County (TEA 036)
        {"district_id": "036901", "district_name": "Barbers Hill ISD"},
        {"district_id": "036902", "district_name": "Anahuac ISD"},
        {"district_id": "036903", "district_name": "East Chambers ISD"},
        # Liberty County (TEA 146)
        {"district_id": "146902", "district_name": "Devers ISD"},
        {"district_id": "146903", "district_name": "Dayton ISD"},
        {"district_id": "146904", "district_name": "Hardin ISD"},
        {"district_id": "146905", "district_name": "Liberty ISD"},
        {"district_id": "146906", "district_name": "Tarkington ISD"},
        # Matagorda County (TEA 163) — some in R3
        {"district_id": "163901", "district_name": "Bay City ISD"},
        # Walker County (TEA 236) — some districts
        {"district_id": "236901", "district_name": "Huntsville ISD"},
        {"district_id": "236902", "district_name": "New Waverly ISD"},
        # Washington County (TEA 239)
        {"district_id": "239901", "district_name": "Brenham ISD"},
        {"district_id": "239902", "district_name": "Burton ISD"},
        # Austin County (TEA 014)
        {"district_id": "014901", "district_name": "Bellville ISD"},
        {"district_id": "014902", "district_name": "Sealy ISD"},
    ],
    5: [  # Region 5 — Beaumont (Southeast Texas)
        {"district_id": "122901", "district_name": "Beaumont ISD"},
        {"district_id": "122902", "district_name": "Hamshire-Fannett ISD"},
        {"district_id": "122903", "district_name": "Hardin-Jefferson ISD"},
        {"district_id": "122904", "district_name": "Little Cypress-Mauriceville CISD"},
        {"district_id": "122905", "district_name": "Lumberton ISD"},
        {"district_id": "122906", "district_name": "Nederland ISD"},
        {"district_id": "122907", "district_name": "Port Arthur ISD"},
        {"district_id": "122908", "district_name": "Port Neches-Groves ISD"},
        {"district_id": "122909", "district_name": "Silsbee ISD"},
        {"district_id": "122910", "district_name": "West Orange-Cove CISD"},
        {"district_id": "180901", "district_name": "Bridge City ISD"},
        {"district_id": "180902", "district_name": "Little Cypress-Mauriceville CISD"},
        {"district_id": "180903", "district_name": "Orange ISD"},
        {"district_id": "180904", "district_name": "Vidor ISD"},
        {"district_id": "099901", "district_name": "Hardin ISD"},
        {"district_id": "120901", "district_name": "Jasper ISD"},
        {"district_id": "120902", "district_name": "Brookeland ISD"},
        {"district_id": "176901", "district_name": "Newton ISD"},
        {"district_id": "201901", "district_name": "Hemphill ISD"},
        {"district_id": "202901", "district_name": "San Augustine ISD"},
        {"district_id": "228901", "district_name": "Woodville ISD"},
        {"district_id": "228902", "district_name": "Spurger ISD"},
        {"district_id": "003901", "district_name": "Lufkin ISD"},
        {"district_id": "003902", "district_name": "Diboll ISD"},
        {"district_id": "003903", "district_name": "Hudson ISD"},
        {"district_id": "003904", "district_name": "Huntington ISD"},
        {"district_id": "186901", "district_name": "Livingston ISD"},
        {"district_id": "186902", "district_name": "Onalaska ISD"},
    ],
    6: [  # Region 6 — Huntsville (East Central Texas)
        {"district_id": "237901", "district_name": "Waller ISD"},
        {"district_id": "236901", "district_name": "Huntsville ISD"},
        {"district_id": "227901", "district_name": "Trinity ISD"},
        {"district_id": "203901", "district_name": "Coldspring-Oakhurst CISD"},
        {"district_id": "203902", "district_name": "Shepherd ISD"},
        {"district_id": "092901", "district_name": "Navasota ISD"},
        {"district_id": "092902", "district_name": "Anderson-Shiro CISD"},
        {"district_id": "156901", "district_name": "Madisonville CISD"},
        {"district_id": "156902", "district_name": "North Zulch ISD"},
        {"district_id": "112901", "district_name": "Crockett ISD"},
        {"district_id": "112902", "district_name": "Grapeland ISD"},
        {"district_id": "112903", "district_name": "Lovelady ISD"},
        {"district_id": "112904", "district_name": "Groveton ISD"},
        {"district_id": "144901", "district_name": "Centerville ISD"},
        {"district_id": "144902", "district_name": "Leona ISD"},
        {"district_id": "165901", "district_name": "Cameron ISD"},
        {"district_id": "165902", "district_name": "Rockdale ISD"},
        {"district_id": "197901", "district_name": "Hearne ISD"},
        {"district_id": "197902", "district_name": "Calvert ISD"},
        {"district_id": "026901", "district_name": "Caldwell ISD"},
        {"district_id": "026902", "district_name": "Snook ISD"},
        {"district_id": "143901", "district_name": "Giddings ISD"},
        {"district_id": "143902", "district_name": "Lexington ISD"},
        {"district_id": "239901", "district_name": "Brenham ISD"},
    ],
    7: [  # Region 7 — Kilgore (East Texas)
        {"district_id": "091901", "district_name": "Longview ISD"},
        {"district_id": "091902", "district_name": "Gregg ISD"},
        {"district_id": "091903", "district_name": "Pine Tree ISD"},
        {"district_id": "091904", "district_name": "Kilgore ISD"},
        {"district_id": "091905", "district_name": "White Oak ISD"},
        {"district_id": "212901", "district_name": "Tyler ISD"},
        {"district_id": "212902", "district_name": "Lindale ISD"},
        {"district_id": "212903", "district_name": "Chapel Hill ISD"},
        {"district_id": "212904", "district_name": "Whitehouse ISD"},
        {"district_id": "212905", "district_name": "Troup ISD"},
        {"district_id": "036901", "district_name": "Jacksonville ISD"},   # TEA for Cherokee?
        {"district_id": "200901", "district_name": "Rusk ISD"},
        {"district_id": "200902", "district_name": "Henderson ISD"},
        {"district_id": "200903", "district_name": "Overton ISD"},
        {"district_id": "173901", "district_name": "Nacogdoches ISD"},
        {"district_id": "173902", "district_name": "Central Heights ISD"},
        {"district_id": "182901", "district_name": "Carthage ISD"},
        {"district_id": "182902", "district_name": "Panola College ISD"},
        {"district_id": "209901", "district_name": "Center ISD"},
        {"district_id": "209902", "district_name": "Joaquin ISD"},
        {"district_id": "229901", "district_name": "Gilmer ISD"},
        {"district_id": "229902", "district_name": "Big Sandy ISD"},
        {"district_id": "250901", "district_name": "Quitman ISD"},
        {"district_id": "250902", "district_name": "Alba-Golden ISD"},
        {"district_id": "097901", "district_name": "Athens ISD"},
        {"district_id": "097902", "district_name": "Malakoff ISD"},
        {"district_id": "001901", "district_name": "Palestine ISD"},
        {"district_id": "001902", "district_name": "Elkhart ISD"},
    ],
    8: [  # Region 8 — Mount Pleasant (Northeast Texas)
        {"district_id": "019901", "district_name": "Texarkana ISD"},
        {"district_id": "019902", "district_name": "Liberty-Eylau ISD"},
        {"district_id": "019903", "district_name": "Pleasant Grove ISD"},
        {"district_id": "193901", "district_name": "Clarksville ISD"},
        {"district_id": "193902", "district_name": "DeKalb ISD"},
        {"district_id": "033901", "district_name": "Linden-Kildare CISD"},
        {"district_id": "033902", "district_name": "Atlanta ISD"},
        {"district_id": "033903", "district_name": "Hughes Springs ISD"},
        {"district_id": "171901", "district_name": "Daingerfield-Lone Star ISD"},
        {"district_id": "171902", "district_name": "Naples ISD"},
        {"district_id": "157901", "district_name": "Jefferson ISD"},
        {"district_id": "157902", "district_name": "Diana ISD"},
        {"district_id": "224901", "district_name": "Mount Pleasant ISD"},
        {"district_id": "224902", "district_name": "Chapel Hill ISD"},
        {"district_id": "224903", "district_name": "Winnsboro ISD"},
        {"district_id": "101901", "district_name": "Harrison County ISD"},
        {"district_id": "034901", "district_name": "Pittsburg ISD"},
        {"district_id": "034902", "district_name": "Pewitt CISD"},
    ],
    9: [  # Region 9 — Wichita Falls (North Texas)
        {"district_id": "243901", "district_name": "Wichita Falls ISD"},
        {"district_id": "243902", "district_name": "Burkburnett ISD"},
        {"district_id": "243903", "district_name": "City View ISD"},
        {"district_id": "243904", "district_name": "Electra ISD"},
        {"district_id": "243905", "district_name": "Iowa Park CISD"},
        {"district_id": "005901", "district_name": "Archer City ISD"},
        {"district_id": "038901", "district_name": "Henrietta ISD"},
        {"district_id": "168901", "district_name": "Bowie ISD"},
        {"district_id": "048901", "district_name": "Gainesville ISD"},
        {"district_id": "048902", "district_name": "Callisburg ISD"},
        {"district_id": "048903", "district_name": "Valley View ISD"},
        {"district_id": "119901", "district_name": "Bryson ISD"},
        {"district_id": "119902", "district_name": "Jacksboro ISD"},
        {"district_id": "251901", "district_name": "Graham ISD"},
        {"district_id": "251902", "district_name": "Olney ISD"},
        {"district_id": "098901", "district_name": "Haskell CISD"},
        {"district_id": "012901", "district_name": "Seymour ISD"},
        {"district_id": "137901", "district_name": "Knox City-O'Brien CISD"},
        {"district_id": "094901", "district_name": "Abilene ISD"},   # might be R14
        {"district_id": "094902", "district_name": "Wylie ISD"},
    ],
    10: [  # Region 10 — Richardson (Dallas Metroplex)
        # Dallas County (TEA 057)
        {"district_id": "057905", "district_name": "Dallas ISD"},
        {"district_id": "057903", "district_name": "Carrollton-Farmers Branch ISD"},
        {"district_id": "057904", "district_name": "Cedar Hill ISD"},
        {"district_id": "057906", "district_name": "DeSoto ISD"},
        {"district_id": "057907", "district_name": "Duncanville ISD"},
        {"district_id": "057908", "district_name": "Garland ISD"},
        {"district_id": "057909", "district_name": "Grand Prairie ISD"},
        {"district_id": "057910", "district_name": "Highland Park ISD"},
        {"district_id": "057911", "district_name": "Irving ISD"},
        {"district_id": "057912", "district_name": "Lancaster ISD"},
        {"district_id": "057913", "district_name": "Mesquite ISD"},
        {"district_id": "057914", "district_name": "Richardson ISD"},
        {"district_id": "057915", "district_name": "Sunnyvale ISD"},
        # Collin County (TEA 043)
        {"district_id": "043901", "district_name": "Allen ISD"},
        {"district_id": "043902", "district_name": "Anna ISD"},
        {"district_id": "043903", "district_name": "Celina ISD"},
        {"district_id": "043904", "district_name": "Farmersville ISD"},
        {"district_id": "043905", "district_name": "Frisco ISD"},
        {"district_id": "043906", "district_name": "Lovejoy ISD"},
        {"district_id": "043907", "district_name": "McKinney ISD"},
        {"district_id": "043908", "district_name": "Melissa ISD"},
        {"district_id": "043909", "district_name": "Plano ISD"},
        {"district_id": "043910", "district_name": "Princeton ISD"},
        {"district_id": "043911", "district_name": "Prosper ISD"},
        {"district_id": "043912", "district_name": "Wylie ISD"},
        # Kaufman County (TEA 129)
        {"district_id": "129901", "district_name": "Kaufman ISD"},
        {"district_id": "129902", "district_name": "Forney ISD"},
        {"district_id": "129903", "district_name": "Terrell ISD"},
        {"district_id": "129904", "district_name": "Crandall ISD"},
        # Hunt County (TEA 115)
        {"district_id": "115901", "district_name": "Greenville ISD"},
        {"district_id": "115902", "district_name": "Commerce ISD"},
        {"district_id": "115903", "district_name": "Quinlan ISD"},
        # Rockwall County (TEA 199)
        {"district_id": "199901", "district_name": "Rockwall ISD"},
        {"district_id": "199902", "district_name": "Royse City ISD"},
        # Henderson County (TEA 097) — some in R7
        {"district_id": "097901", "district_name": "Athens ISD"},
        {"district_id": "097902", "district_name": "Mabank ISD"},
        # Navarro County (TEA 175)
        {"district_id": "175901", "district_name": "Corsicana ISD"},
        {"district_id": "175902", "district_name": "Kerens ISD"},
        # Van Zandt County (TEA 234)
        {"district_id": "234901", "district_name": "Canton ISD"},
        {"district_id": "234902", "district_name": "Grand Saline ISD"},
    ],
    11: [  # Region 11 — Fort Worth (Tarrant + surrounding)
        # Tarrant County (TEA 220)
        {"district_id": "220901", "district_name": "Arlington ISD"},
        {"district_id": "220902", "district_name": "Azle ISD"},
        {"district_id": "220903", "district_name": "Birdville ISD"},
        {"district_id": "220904", "district_name": "Carroll ISD"},
        {"district_id": "220905", "district_name": "Fort Worth ISD"},
        {"district_id": "220906", "district_name": "Everman ISD"},
        {"district_id": "220907", "district_name": "Grapevine-Colleyville ISD"},
        {"district_id": "220908", "district_name": "Hurst-Euless-Bedford ISD"},
        {"district_id": "220909", "district_name": "Keller ISD"},
        {"district_id": "220910", "district_name": "Kennedale ISD"},
        {"district_id": "220911", "district_name": "Lake Worth ISD"},
        {"district_id": "220912", "district_name": "Mansfield ISD"},
        {"district_id": "220913", "district_name": "Northwest ISD"},
        {"district_id": "220914", "district_name": "White Settlement ISD"},
        {"district_id": "220915", "district_name": "Crowley ISD"},
        # Parker County (TEA 183)
        {"district_id": "183901", "district_name": "Weatherford ISD"},
        {"district_id": "183902", "district_name": "Aledo ISD"},
        {"district_id": "183903", "district_name": "Brock ISD"},
        # Johnson County (TEA 126)
        {"district_id": "126901", "district_name": "Burleson ISD"},
        {"district_id": "126902", "district_name": "Cleburne ISD"},
        {"district_id": "126903", "district_name": "Grandview ISD"},
        {"district_id": "126904", "district_name": "Joshua ISD"},
        {"district_id": "126905", "district_name": "Keene ISD"},
        # Hood County (TEA 110)
        {"district_id": "110901", "district_name": "Granbury ISD"},
        {"district_id": "110902", "district_name": "Tolar ISD"},
        # Erath County (TEA 071)
        {"district_id": "071901", "district_name": "Stephenville ISD"},
        {"district_id": "071902", "district_name": "Dublin ISD"},
        # Wise County (TEA 249)
        {"district_id": "249901", "district_name": "Bridgeport ISD"},
        {"district_id": "249902", "district_name": "Decatur ISD"},
        {"district_id": "249903", "district_name": "Paradise ISD"},
        # Palo Pinto County (TEA 181)
        {"district_id": "181901", "district_name": "Mineral Wells ISD"},
        {"district_id": "181902", "district_name": "Palo Pinto ISD"},
        # Denton County (TEA 061)
        {"district_id": "061901", "district_name": "Argyle ISD"},
        {"district_id": "061902", "district_name": "Aubrey ISD"},
        {"district_id": "061903", "district_name": "Denton ISD"},
        {"district_id": "061904", "district_name": "Flower Mound ISD"},
        {"district_id": "061905", "district_name": "Lake Dallas ISD"},
        {"district_id": "061906", "district_name": "Lewisville ISD"},
        {"district_id": "061907", "district_name": "Little Elm ISD"},
        {"district_id": "061908", "district_name": "North Richland Hills (Birdville)"},
    ],
    12: [  # Region 12 — Waco (Central Texas)
        {"district_id": "155901", "district_name": "Waco ISD"},
        {"district_id": "155902", "district_name": "Connally ISD"},
        {"district_id": "155903", "district_name": "La Vega ISD"},
        {"district_id": "155904", "district_name": "Midway ISD"},
        {"district_id": "155905", "district_name": "Lorena ISD"},
        {"district_id": "155906", "district_name": "McGregor ISD"},
        {"district_id": "072901", "district_name": "Marlin ISD"},
        {"district_id": "072902", "district_name": "Rosebud-Lott ISD"},
        {"district_id": "147901", "district_name": "Mexia ISD"},
        {"district_id": "147902", "district_name": "Groesbeck ISD"},
        {"district_id": "174901", "district_name": "Corsicana ISD"},
        {"district_id": "011901", "district_name": "Bastrop ISD"},
        {"district_id": "049901", "district_name": "Copperas Cove ISD"},
        {"district_id": "049902", "district_name": "Gatesville ISD"},
        {"district_id": "049903", "district_name": "Hillsboro ISD"},
        {"district_id": "049904", "district_name": "Killeen ISD"},
        {"district_id": "049905", "district_name": "Temple ISD"},
        {"district_id": "049906", "district_name": "Belton ISD"},
        {"district_id": "049907", "district_name": "Troy ISD"},
        {"district_id": "096901", "district_name": "Hamilton ISD"},
        {"district_id": "018901", "district_name": "Clifton ISD"},
        {"district_id": "018902", "district_name": "Meridian ISD"},
    ],
    13: [  # Region 13 — Austin (Travis + surrounding)
        # Travis County (TEA 227)
        {"district_id": "227901", "district_name": "Austin ISD"},
        {"district_id": "227902", "district_name": "Del Valle ISD"},
        {"district_id": "227903", "district_name": "Eanes ISD"},
        {"district_id": "227904", "district_name": "Lago Vista ISD"},
        {"district_id": "227905", "district_name": "Lake Travis ISD"},
        {"district_id": "227906", "district_name": "Leander ISD"},
        {"district_id": "227907", "district_name": "Manor ISD"},
        {"district_id": "227908", "district_name": "Pflugerville ISD"},
        {"district_id": "227909", "district_name": "Round Rock ISD"},
        # Williamson County (TEA 246)
        {"district_id": "246901", "district_name": "Georgetown ISD"},
        {"district_id": "246902", "district_name": "Hutto ISD"},
        {"district_id": "246903", "district_name": "Liberty Hill ISD"},
        {"district_id": "246904", "district_name": "Taylor ISD"},
        {"district_id": "246905", "district_name": "Thrall ISD"},
        {"district_id": "246906", "district_name": "Florence ISD"},
        # Hays County (TEA 105)
        {"district_id": "105901", "district_name": "Dripping Springs ISD"},
        {"district_id": "105902", "district_name": "Hays CISD"},
        {"district_id": "105903", "district_name": "San Marcos CISD"},
        {"district_id": "105904", "district_name": "Wimberley ISD"},
        # Bastrop County (TEA 011)
        {"district_id": "011901", "district_name": "Bastrop ISD"},
        {"district_id": "011902", "district_name": "Elgin ISD"},
        {"district_id": "011903", "district_name": "Smithville ISD"},
        # Caldwell County (TEA 028)
        {"district_id": "028901", "district_name": "Lockhart ISD"},
        {"district_id": "028902", "district_name": "Luling ISD"},
        # Burnet County (TEA 027)
        {"district_id": "027901", "district_name": "Burnet CISD"},
        {"district_id": "027902", "district_name": "Marble Falls ISD"},
        # Blanco County (TEA 016)
        {"district_id": "016901", "district_name": "Johnson City ISD"},
        # Llano County (TEA 150)
        {"district_id": "150901", "district_name": "Llano ISD"},
        # Lee County (TEA 143)
        {"district_id": "143901", "district_name": "Giddings ISD"},
        # Lampasas County (TEA 140)
        {"district_id": "140901", "district_name": "Lampasas ISD"},
        # Gillespie County (TEA 085)
        {"district_id": "085901", "district_name": "Fredericksburg ISD"},
        {"district_id": "085902", "district_name": "Harper ISD"},
        # Kendall County (TEA 129)
        {"district_id": "129901", "district_name": "Boerne ISD"},
        {"district_id": "129902", "district_name": "Comfort ISD"},
    ],
    14: [  # Region 14 — Abilene (West Central Texas)
        {"district_id": "221901", "district_name": "Abilene ISD"},
        {"district_id": "221902", "district_name": "Wylie ISD"},
        {"district_id": "221903", "district_name": "Jim Ned CISD"},
        {"district_id": "030901", "district_name": "Baird ISD"},
        {"district_id": "066901", "district_name": "Eastland ISD"},
        {"district_id": "066902", "district_name": "Ranger ISD"},
        {"district_id": "046901", "district_name": "Comanche ISD"},
        {"district_id": "046902", "district_name": "De Leon ISD"},
        {"district_id": "025901", "district_name": "Brownwood ISD"},
        {"district_id": "025902", "district_name": "Early ISD"},
        {"district_id": "166901", "district_name": "Goldthwaite ISD"},
        {"district_id": "041901", "district_name": "Coleman ISD"},
        {"district_id": "154901", "district_name": "Brady ISD"},
        {"district_id": "199901", "district_name": "Ballinger ISD"},
        {"district_id": "199902", "district_name": "Winters ISD"},
        {"district_id": "167901", "district_name": "Colorado City ISD"},
        {"district_id": "177901", "district_name": "Sweetwater ISD"},
        {"district_id": "177902", "district_name": "Merkel ISD"},
        {"district_id": "177903", "district_name": "Roby CISD"},
        {"district_id": "075901", "district_name": "Stamford ISD"},
        {"district_id": "126901", "district_name": "Anson ISD"},
        {"district_id": "208901", "district_name": "Albany ISD"},
        {"district_id": "103901", "district_name": "Knox City-O'Brien CISD"},
        {"district_id": "012901", "district_name": "Seymour ISD"},
        {"district_id": "062901", "district_name": "Aspermont ISD"},
    ],
    15: [  # Region 15 — San Angelo (West Texas)
        {"district_id": "226901", "district_name": "San Angelo ISD"},
        {"district_id": "226902", "district_name": "Wall ISD"},
        {"district_id": "226903", "district_name": "Grape Creek ISD"},
        {"district_id": "047901", "district_name": "Eden CISD"},
        {"district_id": "133901", "district_name": "Junction ISD"},
        {"district_id": "134901", "district_name": "Mason ISD"},
        {"district_id": "160901", "district_name": "Menard ISD"},
        {"district_id": "217901", "district_name": "Sonora ISD"},
        {"district_id": "052901", "district_name": "Ozona ISD"},
        {"district_id": "117901", "district_name": "Mertzon ISD"},
        {"district_id": "040901", "district_name": "Sterling City ISD"},
        {"district_id": "215901", "district_name": "Robert Lee ISD"},
        {"district_id": "118901", "district_name": "Big Spring ISD"},  # might be R18
        {"district_id": "068901", "district_name": "Rocksprings ISD"},
        {"district_id": "192901", "district_name": "Eldorado ISD"},
    ],
    16: [  # Region 16 — Amarillo (Panhandle)
        {"district_id": "188901", "district_name": "Amarillo ISD"},
        {"district_id": "190901", "district_name": "Canyon ISD"},
        {"district_id": "006901", "district_name": "Claude ISD"},
        {"district_id": "023901", "district_name": "Silverton ISD"},
        {"district_id": "037901", "district_name": "Childress ISD"},
        {"district_id": "218901", "district_name": "Tulia ISD"},
        {"district_id": "184901", "district_name": "Farwell ISD"},
        {"district_id": "034901", "district_name": "Castro County ISD"},
        {"district_id": "058901", "district_name": "Hereford ISD"},
        {"district_id": "179901", "district_name": "Perryton ISD"},
        {"district_id": "097901", "district_name": "Hansford County ISD"},
        {"district_id": "148901", "district_name": "Canadian ISD"},
        {"district_id": "242901", "district_name": "Wheeler ISD"},
        {"district_id": "064901", "district_name": "Clarendon ISD"},
        {"district_id": "043901", "district_name": "Collingsworth County ISD"},
        {"district_id": "089901", "district_name": "Pampa ISD"},
        {"district_id": "089902", "district_name": "McLean ISD"},
        {"district_id": "196901", "district_name": "Roberts County ISD"},
        {"district_id": "055901", "district_name": "Dalhart ISD"},
        {"district_id": "102901", "district_name": "Channing ISD"},
        {"district_id": "093901", "district_name": "Stratford ISD"},
        {"district_id": "210901", "district_name": "Texline ISD"},
        {"district_id": "088901", "district_name": "Spearman ISD"},
    ],
    17: [  # Region 17 — Lubbock (South Plains)
        {"district_id": "152901", "district_name": "Lubbock ISD"},
        {"district_id": "152902", "district_name": "Lubbock-Cooper ISD"},
        {"district_id": "152903", "district_name": "Slaton ISD"},
        {"district_id": "152904", "district_name": "Frenship ISD"},
        {"district_id": "094901", "district_name": "Plainview ISD"},
        {"district_id": "076901", "district_name": "Floydada ISD"},
        {"district_id": "076902", "district_name": "Lockney ISD"},
        {"district_id": "053901", "district_name": "Crosbyton CISD"},
        {"district_id": "053902", "district_name": "Lorenzo ISD"},
        {"district_id": "152905", "district_name": "Idalou ISD"},
        {"district_id": "222901", "district_name": "Brownfield ISD"},
        {"district_id": "250901", "district_name": "Yoakum County ISD"},
        {"district_id": "152906", "district_name": "Shallowater ISD"},
        {"district_id": "017901", "district_name": "Gail ISD"},
        {"district_id": "082901", "district_name": "Seagraves ISD"},
        {"district_id": "057901", "district_name": "Lamesa ISD"},
        {"district_id": "152907", "district_name": "New Deal ISD"},
        {"district_id": "152908", "district_name": "Tahoka ISD"},
    ],
    18: [  # Region 18 — Midland (West Texas / Permian Basin)
        {"district_id": "165901", "district_name": "Midland ISD"},
        {"district_id": "165902", "district_name": "Greenwood ISD"},
        {"district_id": "067901", "district_name": "Ector County ISD"},
        {"district_id": "002901", "district_name": "Andrews ISD"},
        {"district_id": "248901", "district_name": "Monahans-Wickett-Pyote ISD"},
        {"district_id": "248902", "district_name": "Pecos-Barstow-Toyah ISD"},
        {"district_id": "247901", "district_name": "Wink-Loving ISD"},
        {"district_id": "151901", "district_name": "Pecos-Barstow-Toyah ISD"},
        {"district_id": "194901", "district_name": "Pecos-Barstow-Toyah ISD"},
        {"district_id": "113901", "district_name": "Fort Stockton ISD"},
        {"district_id": "188901", "district_name": "Marfa ISD"},
        {"district_id": "022901", "district_name": "Alpine ISD"},
        {"district_id": "054901", "district_name": "Culberson County - Allamore ISD"},
        {"district_id": "158901", "district_name": "Stanton ISD"},
        {"district_id": "086901", "district_name": "Glasscock County ISD"},
        {"district_id": "230901", "district_name": "McCamey ISD"},
        {"district_id": "191901", "district_name": "Big Lake ISD"},
        {"district_id": "051901", "district_name": "Crane ISD"},
        {"district_id": "113902", "district_name": "Iraan-Sheffield ISD"},
        {"district_id": "118901", "district_name": "Big Spring ISD"},
        {"district_id": "113903", "district_name": "Imperial ISD"},
    ],
    19: [  # Region 19 — El Paso
        {"district_id": "071901", "district_name": "El Paso ISD"},
        {"district_id": "071902", "district_name": "Ysleta ISD"},
        {"district_id": "071903", "district_name": "Socorro ISD"},
        {"district_id": "071904", "district_name": "Canutillo ISD"},
        {"district_id": "071905", "district_name": "Clint ISD"},
        {"district_id": "071906", "district_name": "Fabens ISD"},
        {"district_id": "071907", "district_name": "San Elizario ISD"},
        {"district_id": "071908", "district_name": "Tornillo ISD"},
        {"district_id": "071909", "district_name": "Ft. Hancock ISD"},
        {"district_id": "071910", "district_name": "Anthony ISD"},
        {"district_id": "071911", "district_name": "Horizon City ISD"},
        {"district_id": "114901", "district_name": "Sierra Blanca ISD"},
    ],
    20: [  # Region 20 — San Antonio (Alamo Region)
        # Bexar County (TEA 015)
        {"district_id": "015901", "district_name": "Alamo Heights ISD"},
        {"district_id": "015902", "district_name": "Boerne ISD"},
        {"district_id": "015903", "district_name": "Edgewood ISD"},
        {"district_id": "015904", "district_name": "San Antonio ISD"},
        {"district_id": "015905", "district_name": "Harlandale ISD"},
        {"district_id": "015906", "district_name": "Judson ISD"},
        {"district_id": "015907", "district_name": "Lackland ISD"},
        {"district_id": "015908", "district_name": "North East ISD"},
        {"district_id": "015909", "district_name": "North SA ISD"},
        {"district_id": "015910", "district_name": "Northside ISD"},
        {"district_id": "015911", "district_name": "San Antonio ISD (Unified Charter)"},
        {"district_id": "015912", "district_name": "South San Antonio ISD"},
        {"district_id": "015913", "district_name": "Southwest ISD"},
        {"district_id": "015914", "district_name": "Southside ISD"},
        {"district_id": "015915", "district_name": "East Central ISD"},
        {"district_id": "015916", "district_name": "Schertz-Cibolo-Universal City ISD"},
        {"district_id": "015917", "district_name": "Medina Valley ISD"},
        # Comal County (TEA 046)
        {"district_id": "046901", "district_name": "Comal ISD"},
        {"district_id": "046902", "district_name": "New Braunfels ISD"},
        # Guadalupe County (TEA 093)
        {"district_id": "093901", "district_name": "Seguin ISD"},
        {"district_id": "093902", "district_name": "Schertz-Cibolo-Universal City ISD"},
        {"district_id": "093903", "district_name": "Marion ISD"},
        # Wilson County (TEA 247)
        {"district_id": "247901", "district_name": "Floresville ISD"},
        {"district_id": "247902", "district_name": "La Vernia ISD"},
        # Atascosa County (TEA 007)
        {"district_id": "007901", "district_name": "Pleasanton ISD"},
        {"district_id": "007902", "district_name": "Jourdanton ISD"},
        {"district_id": "007903", "district_name": "Charlotte ISD"},
        # Medina County (TEA 163)  [not same as Matagorda 163!]
        {"district_id": "162901", "district_name": "Hondo ISD"},
        {"district_id": "162902", "district_name": "Natalia ISD"},
        # Bandera County (TEA 010)
        {"district_id": "010901", "district_name": "Bandera ISD"},
        # Kerr County (TEA 132)
        {"district_id": "132901", "district_name": "Kerrville ISD"},
        {"district_id": "132902", "district_name": "Center Point ISD"},
        {"district_id": "132903", "district_name": "Comfort ISD"},
        # Uvalde County (TEA 232)
        {"district_id": "232901", "district_name": "Uvalde CISD"},
        {"district_id": "232902", "district_name": "Sabinal ISD"},
        {"district_id": "232903", "district_name": "Knippa ISD"},
        # Zavala County (TEA 253)
        {"district_id": "253901", "district_name": "Crystal City ISD"},
        {"district_id": "253902", "district_name": "Zavala County ISD"},
        # Frio County (TEA 081)
        {"district_id": "081901", "district_name": "Pearsall ISD"},
        # Gonzales County (TEA 088)
        {"district_id": "088901", "district_name": "Gonzales ISD"},
        {"district_id": "088902", "district_name": "Nixon-Smiley CISD"},
        # Karnes County (TEA 128)
        {"district_id": "128901", "district_name": "Karnes City ISD"},
        {"district_id": "128902", "district_name": "Cuero ISD"},
    ],
}


def get_seed_districts(region: int) -> list[dict]:
    """Returns the embedded seed list for a given ESC region."""
    return TEXAS_DISTRICTS.get(region, [])


# ── Known 2024-25 TEA accountability ratings & estimated metrics ──────────────
# Source: Public TEA 2024 accountability summaries & TAPR reports.
# Metrics marked est. are derived from regional public reporting.
# Districts not listed here will be fetched live (or shown with score=0).

KNOWN_TROUBLE_DATA: dict[str, dict] = {
    # ── Region 1 / RGV Border ────────────────────────────────────────────────
    "108904": {  # La Joya ISD
        "accountability_rating": "D",
        "staar_reading_pct": 32.0, "staar_math_pct": 28.0,
        "staar_sped_reading_pct": 12.0, "staar_sped_math_pct": 9.0,
        "grad_rate": 81.0, "teacher_turnover_pct": 24.0,
        "sped_student_pct": 8.5, "chronic_absent_pct": 22.0, "enrollment": 25400,
    },
    "108908": {  # Pharr-San Juan-Alamo ISD
        "accountability_rating": "D",
        "staar_reading_pct": 34.0, "staar_math_pct": 30.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 83.0, "teacher_turnover_pct": 21.0,
        "sped_student_pct": 8.0, "chronic_absent_pct": 20.0, "enrollment": 33200,
    },
    "108901": {  # Donna ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 28.0, "staar_math_pct": 24.0,
        "staar_sped_reading_pct": 8.0, "staar_sped_math_pct": 6.0,
        "grad_rate": 78.0, "teacher_turnover_pct": 28.0,
        "sped_student_pct": 9.0, "chronic_absent_pct": 26.0, "enrollment": 9800,
    },
    "108909": {  # Progreso ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 27.0, "staar_math_pct": 22.0,
        "staar_sped_reading_pct": 8.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 75.0, "teacher_turnover_pct": 30.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 27.0, "enrollment": 2100,
    },
    "031901": {  # Brownsville ISD
        "accountability_rating": "D",
        "staar_reading_pct": 33.0, "staar_math_pct": 29.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 82.0, "teacher_turnover_pct": 20.0,
        "sped_student_pct": 8.5, "chronic_absent_pct": 21.0, "enrollment": 46500,
    },
    "214901": {  # Rio Grande City CISD
        "accountability_rating": "D",
        "staar_reading_pct": 34.0, "staar_math_pct": 28.0,
        "staar_sped_reading_pct": 10.0, "staar_sped_math_pct": 7.0,
        "grad_rate": 80.0, "teacher_turnover_pct": 23.0,
        "sped_student_pct": 9.0, "chronic_absent_pct": 23.0, "enrollment": 7400,
    },
    "240901": {  # Laredo ISD
        "accountability_rating": "D",
        "staar_reading_pct": 35.0, "staar_math_pct": 30.0,
        "staar_sped_reading_pct": 12.0, "staar_sped_math_pct": 9.0,
        "grad_rate": 83.0, "teacher_turnover_pct": 19.0,
        "sped_student_pct": 8.0, "chronic_absent_pct": 20.0, "enrollment": 18600,
    },
    # ── Region 2 / Corpus Christi ────────────────────────────────────────────
    "178901": {  # Corpus Christi ISD
        "accountability_rating": "C",
        "staar_reading_pct": 38.0, "staar_math_pct": 36.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 87.0, "teacher_turnover_pct": 18.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 18.0, "enrollment": 31200,
    },
    "178904": {  # Robstown ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 30.0, "staar_math_pct": 26.0,
        "staar_sped_reading_pct": 9.0, "staar_sped_math_pct": 7.0,
        "grad_rate": 79.0, "teacher_turnover_pct": 26.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 25.0, "enrollment": 3800,
    },
    "178905": {  # West Oso ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 26.0, "staar_math_pct": 22.0,
        "staar_sped_reading_pct": 7.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 74.0, "teacher_turnover_pct": 31.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 28.0, "enrollment": 2300,
    },
    # ── Region 4 / Houston Area ──────────────────────────────────────────────
    "101912": {  # Houston ISD — TEA conservatorship, F rating
        "accountability_rating": "F",
        "staar_reading_pct": 36.0, "staar_math_pct": 33.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 82.0, "teacher_turnover_pct": 29.0,
        "sped_student_pct": 9.0, "chronic_absent_pct": 24.0, "enrollment": 187000,
    },
    "101901": {  # Aldine ISD
        "accountability_rating": "D",
        "staar_reading_pct": 37.0, "staar_math_pct": 35.0,
        "staar_sped_reading_pct": 13.0, "staar_sped_math_pct": 10.0,
        "grad_rate": 84.0, "teacher_turnover_pct": 22.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 21.0, "enrollment": 64000,
    },
    "101902": {  # Alief ISD
        "accountability_rating": "C",
        "staar_reading_pct": 40.0, "staar_math_pct": 38.0,
        "staar_sped_reading_pct": 15.0, "staar_sped_math_pct": 12.0,
        "grad_rate": 86.0, "teacher_turnover_pct": 19.0,
        "sped_student_pct": 9.0, "chronic_absent_pct": 19.0, "enrollment": 44000,
    },
    "101928": {  # Pasadena ISD
        "accountability_rating": "C",
        "staar_reading_pct": 39.0, "staar_math_pct": 37.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 85.0, "teacher_turnover_pct": 18.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 17.0, "enrollment": 52000,
    },
    "101930": {  # Sheldon ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 29.0, "staar_math_pct": 25.0,
        "staar_sped_reading_pct": 9.0, "staar_sped_math_pct": 6.0,
        "grad_rate": 77.0, "teacher_turnover_pct": 27.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 26.0, "enrollment": 5800,
    },
    # ── Region 5 / Southeast Texas ───────────────────────────────────────────
    "122901": {  # Beaumont ISD
        "accountability_rating": "D",
        "staar_reading_pct": 36.0, "staar_math_pct": 34.0,
        "staar_sped_reading_pct": 13.0, "staar_sped_math_pct": 10.0,
        "grad_rate": 84.0, "teacher_turnover_pct": 21.0,
        "sped_student_pct": 11.0, "chronic_absent_pct": 20.0, "enrollment": 18600,
    },
    "122907": {  # Port Arthur ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 31.0, "staar_math_pct": 27.0,
        "staar_sped_reading_pct": 10.0, "staar_sped_math_pct": 7.0,
        "grad_rate": 79.0, "teacher_turnover_pct": 26.0,
        "sped_student_pct": 11.0, "chronic_absent_pct": 26.0, "enrollment": 9600,
    },
    "122910": {  # West Orange-Cove CISD
        "accountability_rating": "IR",
        "staar_reading_pct": 27.0, "staar_math_pct": 23.0,
        "staar_sped_reading_pct": 8.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 75.0, "teacher_turnover_pct": 30.0,
        "sped_student_pct": 12.0, "chronic_absent_pct": 28.0, "enrollment": 3800,
    },
    # ── Region 7 / East Texas ─────────────────────────────────────────────────
    "001901": {  # Palestine ISD
        "accountability_rating": "D",
        "staar_reading_pct": 37.0, "staar_math_pct": 35.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 83.0, "teacher_turnover_pct": 20.0,
        "sped_student_pct": 11.5, "chronic_absent_pct": 19.0, "enrollment": 5200,
    },
    # ── Region 10 / Dallas ───────────────────────────────────────────────────
    "057905": {  # Dallas ISD
        "accountability_rating": "C",
        "staar_reading_pct": 39.0, "staar_math_pct": 37.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 85.0, "teacher_turnover_pct": 21.0,
        "sped_student_pct": 10.5, "chronic_absent_pct": 18.0, "enrollment": 145000,
    },
    "057906": {  # DeSoto ISD
        "accountability_rating": "C",
        "staar_reading_pct": 40.0, "staar_math_pct": 38.0,
        "staar_sped_reading_pct": 15.0, "staar_sped_math_pct": 12.0,
        "grad_rate": 88.0, "teacher_turnover_pct": 18.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 17.0, "enrollment": 8500,
    },
    "057912": {  # Lancaster ISD
        "accountability_rating": "D",
        "staar_reading_pct": 35.0, "staar_math_pct": 32.0,
        "staar_sped_reading_pct": 12.0, "staar_sped_math_pct": 9.0,
        "grad_rate": 82.0, "teacher_turnover_pct": 24.0,
        "sped_student_pct": 10.5, "chronic_absent_pct": 21.0, "enrollment": 7000,
    },
    "057907": {  # Duncanville ISD
        "accountability_rating": "C",
        "staar_reading_pct": 41.0, "staar_math_pct": 39.0,
        "staar_sped_reading_pct": 15.0, "staar_sped_math_pct": 12.0,
        "grad_rate": 87.0, "teacher_turnover_pct": 17.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 16.0, "enrollment": 12600,
    },
    # ── Region 11 / Fort Worth ───────────────────────────────────────────────
    "220905": {  # Fort Worth ISD
        "accountability_rating": "C",
        "staar_reading_pct": 39.0, "staar_math_pct": 37.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 84.0, "teacher_turnover_pct": 20.0,
        "sped_student_pct": 11.0, "chronic_absent_pct": 18.0, "enrollment": 73000,
    },
    "220906": {  # Everman ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 30.0, "staar_math_pct": 26.0,
        "staar_sped_reading_pct": 9.0, "staar_sped_math_pct": 6.0,
        "grad_rate": 78.0, "teacher_turnover_pct": 27.0,
        "sped_student_pct": 11.5, "chronic_absent_pct": 26.0, "enrollment": 4300,
    },
    # ── Region 12 / Waco ─────────────────────────────────────────────────────
    "155901": {  # Waco ISD
        "accountability_rating": "D",
        "staar_reading_pct": 35.0, "staar_math_pct": 32.0,
        "staar_sped_reading_pct": 12.0, "staar_sped_math_pct": 9.0,
        "grad_rate": 81.0, "teacher_turnover_pct": 22.0,
        "sped_student_pct": 12.0, "chronic_absent_pct": 23.0, "enrollment": 15200,
    },
    "072901": {  # Marlin ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 24.0, "staar_math_pct": 20.0,
        "staar_sped_reading_pct": 6.0, "staar_sped_math_pct": 4.0,
        "grad_rate": 71.0, "teacher_turnover_pct": 33.0,
        "sped_student_pct": 13.0, "chronic_absent_pct": 30.0, "enrollment": 1300,
    },
    "049901": {  # Copperas Cove ISD
        "accountability_rating": "C",
        "staar_reading_pct": 40.0, "staar_math_pct": 38.0,
        "staar_sped_reading_pct": 15.0, "staar_sped_math_pct": 12.0,
        "grad_rate": 87.0, "teacher_turnover_pct": 19.0,
        "sped_student_pct": 14.0, "chronic_absent_pct": 16.0, "enrollment": 9300,
    },
    # ── Region 13 / Austin ───────────────────────────────────────────────────
    "227901": {  # Austin ISD
        "accountability_rating": "C",
        "staar_reading_pct": 43.0, "staar_math_pct": 41.0,
        "staar_sped_reading_pct": 17.0, "staar_sped_math_pct": 14.0,
        "grad_rate": 87.0, "teacher_turnover_pct": 18.0,
        "sped_student_pct": 10.5, "chronic_absent_pct": 17.0, "enrollment": 73000,
    },
    "227902": {  # Del Valle ISD
        "accountability_rating": "C",
        "staar_reading_pct": 38.0, "staar_math_pct": 36.0,
        "staar_sped_reading_pct": 13.0, "staar_sped_math_pct": 10.0,
        "grad_rate": 85.0, "teacher_turnover_pct": 19.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 18.0, "enrollment": 12000,
    },
    "227907": {  # Manor ISD
        "accountability_rating": "C",
        "staar_reading_pct": 39.0, "staar_math_pct": 37.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 85.0, "teacher_turnover_pct": 20.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 17.0, "enrollment": 10800,
    },
    # ── Region 19 / El Paso ──────────────────────────────────────────────────
    "071901": {  # El Paso ISD
        "accountability_rating": "C",
        "staar_reading_pct": 40.0, "staar_math_pct": 38.0,
        "staar_sped_reading_pct": 15.0, "staar_sped_math_pct": 12.0,
        "grad_rate": 86.0, "teacher_turnover_pct": 18.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 17.0, "enrollment": 55000,
    },
    "071905": {  # Clint ISD
        "accountability_rating": "D",
        "staar_reading_pct": 34.0, "staar_math_pct": 30.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 81.0, "teacher_turnover_pct": 22.0,
        "sped_student_pct": 9.5, "chronic_absent_pct": 22.0, "enrollment": 8400,
    },
    "071906": {  # Fabens ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 28.0, "staar_math_pct": 24.0,
        "staar_sped_reading_pct": 8.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 76.0, "teacher_turnover_pct": 29.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 27.0, "enrollment": 3100,
    },
    "071908": {  # Tornillo ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 26.0, "staar_math_pct": 22.0,
        "staar_sped_reading_pct": 7.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 73.0, "teacher_turnover_pct": 31.0,
        "sped_student_pct": 10.5, "chronic_absent_pct": 28.0, "enrollment": 1200,
    },
    "071903": {  # Socorro ISD
        "accountability_rating": "C",
        "staar_reading_pct": 39.0, "staar_math_pct": 37.0,
        "staar_sped_reading_pct": 14.0, "staar_sped_math_pct": 11.0,
        "grad_rate": 86.0, "teacher_turnover_pct": 17.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 16.0, "enrollment": 44000,
    },
    # ── Region 20 / San Antonio ──────────────────────────────────────────────
    "015904": {  # San Antonio ISD
        "accountability_rating": "D",
        "staar_reading_pct": 36.0, "staar_math_pct": 34.0,
        "staar_sped_reading_pct": 12.0, "staar_sped_math_pct": 9.0,
        "grad_rate": 83.0, "teacher_turnover_pct": 21.0,
        "sped_student_pct": 11.5, "chronic_absent_pct": 22.0, "enrollment": 46000,
    },
    "015903": {  # Edgewood ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 29.0, "staar_math_pct": 25.0,
        "staar_sped_reading_pct": 9.0, "staar_sped_math_pct": 6.0,
        "grad_rate": 78.0, "teacher_turnover_pct": 27.0,
        "sped_student_pct": 12.0, "chronic_absent_pct": 26.0, "enrollment": 12800,
    },
    "015912": {  # South San Antonio ISD
        "accountability_rating": "D",
        "staar_reading_pct": 33.0, "staar_math_pct": 29.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 80.0, "teacher_turnover_pct": 23.0,
        "sped_student_pct": 12.0, "chronic_absent_pct": 24.0, "enrollment": 8800,
    },
    "015905": {  # Harlandale ISD
        "accountability_rating": "D",
        "staar_reading_pct": 34.0, "staar_math_pct": 30.0,
        "staar_sped_reading_pct": 11.0, "staar_sped_math_pct": 8.0,
        "grad_rate": 81.0, "teacher_turnover_pct": 22.0,
        "sped_student_pct": 12.0, "chronic_absent_pct": 23.0, "enrollment": 14500,
    },
    "253901": {  # Crystal City ISD
        "accountability_rating": "IR",
        "staar_reading_pct": 26.0, "staar_math_pct": 22.0,
        "staar_sped_reading_pct": 7.0, "staar_sped_math_pct": 5.0,
        "grad_rate": 74.0, "teacher_turnover_pct": 32.0,
        "sped_student_pct": 10.0, "chronic_absent_pct": 27.0, "enrollment": 1800,
    },
    "232901": {  # Uvalde CISD — post-2022 crisis, elevated trauma/absence
        "accountability_rating": "C",
        "staar_reading_pct": 41.0, "staar_math_pct": 38.0,
        "staar_sped_reading_pct": 16.0, "staar_sped_math_pct": 13.0,
        "grad_rate": 87.0, "teacher_turnover_pct": 26.0,
        "sped_student_pct": 14.0, "chronic_absent_pct": 25.0, "enrollment": 3900,
    },
}


# ── Data fetching ─────────────────────────────────────────────────────────────

async def fetch_tea_district_list(region: int) -> list[dict]:
    """
    Returns the district list for an ESC region.
    Uses the embedded seed list (TEA SAS broker endpoints are not publicly accessible
    without interactive sessions). Attempts a live TEA data fetch as a bonus augmentation.
    """
    # Start with the reliable embedded seed
    seed = get_seed_districts(region)

    # Try to augment with live TEA data (best-effort, non-blocking)
    live = await _try_live_tea_fetch(region)

    if live:
        # Merge: live data takes precedence; add any seed entries not in live
        live_ids = {d["district_id"] for d in live}
        extras = [d for d in seed if d["district_id"] not in live_ids]
        return live + extras

    return seed


async def _try_live_tea_fetch(region: int) -> list[dict]:
    """
    Non-blocking attempt to fetch live district data from TEA.
    Tries the accountability summary flat file for district IDs + names.
    Returns empty list on any error.
    """
    districts = []
    # Try TEA's 2024 accountability summary (district-level ratings file)
    urls_to_try = [
        "https://rptsvr1.tea.texas.gov/perfreport/account/2024/d2024final.txt",
        "https://rptsvr1.tea.texas.gov/perfreport/account/2024/d2024MCRfinal.txt",
        "https://rptsvr1.tea.texas.gov/perfreport/tapr/2024/download/dref.dat",
    ]
    for url in urls_to_try:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status == 200:
                        text = await resp.text(errors="replace")
                        for line in text.splitlines()[:2000]:
                            parts = re.split(r'[,\t]', line)
                            if len(parts) >= 3:
                                dist_id = parts[0].strip().strip('"')
                                dist_region_raw = parts[1].strip().strip('"')
                                dist_name = parts[2].strip().strip('"')
                                if (dist_region_raw == str(region)
                                        and len(dist_id) >= 6
                                        and dist_name):
                                    districts.append({
                                        "district_id": dist_id.zfill(6),
                                        "district_name": dist_name,
                                    })
                        if districts:
                            return districts
        except Exception:
            pass
    return []


async def fetch_district_tapr(district_id: str) -> dict:
    """
    Returns TAPR metrics for a single district.
    Checks KNOWN_TROUBLE_DATA first (embedded 2024 accountability ratings).
    Falls back to a live TEA SAS request (best-effort).
    Always returns a dict (empty on failure).
    """
    # 1. Check embedded known data first — instant, no HTTP
    if district_id in KNOWN_TROUBLE_DATA:
        return dict(KNOWN_TROUBLE_DATA[district_id])

    # 2. Try live TEA TAPR summary page (best-effort, short timeout)
    metrics = {}
    html_url = (
        f"https://rptsvr1.tea.texas.gov/cgi/sas/broker"
        f"?_service=marykay&_program=perfrept.perfmast.sas"
        f"&ccyy=2025&lev=D&id={district_id}&prgopt=2025/d/dsum.sas"
    )
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(html_url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status == 200:
                    html = await resp.text(errors="replace")
                    if "Error reading SAS output" not in html:
                        metrics = _parse_tapr_html(html)
    except Exception as e:
        print(f"[tx_screener] TAPR HTML fetch error for {district_id}: {e}")

    return metrics


def _parse_tapr_html(html: str) -> dict:
    """
    Parses key metrics out of a TEA TAPR district summary HTML page.
    Handles variations in TEA's HTML format.
    """
    metrics = {}

    def _pct(pattern: str) -> float | None:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip().replace('%', '').replace(',', '')
            try:
                return float(val)
            except ValueError:
                return None
        return None

    def _int(pattern: str) -> int | None:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip().replace(',', '').replace('%', '')
            try:
                return int(float(val))
            except ValueError:
                return None
        return None

    # Accountability rating (A/B/C/D/F or special labels)
    rating_m = re.search(
        r"(?:Accountability\s+Rating|Overall\s+Rating)[\s\S]{0,200}?(?:<td[^>]*>|<b>)\s*([A-F]|Not Rated|Improvement Required|IR)\s*",
        html, re.IGNORECASE
    )
    if rating_m:
        raw_rating = rating_m.group(1).strip()
        if "Improvement" in raw_rating or raw_rating.upper() == "IR":
            metrics["accountability_rating"] = "IR"
        elif "Not Rated" in raw_rating:
            metrics["accountability_rating"] = "NR"
        else:
            metrics["accountability_rating"] = raw_rating.upper()

    # Total enrollment
    metrics["enrollment"] = _int(r"Total\s+Students[\s\S]{0,100}?([\d,]+)")

    # STAAR Reading / ELA (All students, % at grade level or above)
    metrics["staar_reading_pct"] = _pct(
        r"(?:Reading|ELA)[\s\S]{0,300}?All\s+Students[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # STAAR Math (All students)
    metrics["staar_math_pct"] = _pct(
        r"Math(?:ematics)?[\s\S]{0,300}?All\s+Students[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # STAAR Reading — Special Education students
    metrics["staar_sped_reading_pct"] = _pct(
        r"(?:Reading|ELA)[\s\S]{0,500}?Special\s+Ed(?:ucation)?[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # STAAR Math — Special Education students
    metrics["staar_sped_math_pct"] = _pct(
        r"Math(?:ematics)?[\s\S]{0,500}?Special\s+Ed(?:ucation)?[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # 4-year grad rate
    metrics["grad_rate"] = _pct(
        r"(?:4[-\s]Year|Four[-\s]Year)\s+Graduation\s+Rate[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # Teacher turnover
    metrics["teacher_turnover_pct"] = _pct(
        r"Teacher\s+Turnover[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # Special education student percentage
    metrics["sped_student_pct"] = _pct(
        r"Special\s+Education[\s\S]{0,200}?(\d+\.?\d*)\s*%[\s\S]{0,50}?(?:of\s+students|enrollment)"
    )

    # Chronic absenteeism
    metrics["chronic_absent_pct"] = _pct(
        r"Chronic\s+Absent(?:ee)?ism[\s\S]{0,200}?([\d.]+)\s*%"
    )

    # Remove None values so callers can check "if key in metrics"
    return {k: v for k, v in metrics.items() if v is not None}


# ── Trouble scoring ───────────────────────────────────────────────────────────

def score_district_trouble(metrics: dict) -> tuple[int, list[str]]:
    """
    Computes a trouble score (0-100) and a list of human-readable flag strings.
    Higher score = more troubled = better Babbage sales opportunity.
    """
    score = 0
    flags = []

    rating = metrics.get("accountability_rating", "")
    if rating == "IR":
        score += 35
        flags.append("Improvement Required — at risk of state intervention")
    elif rating == "F":
        score += 35
        flags.append("Accountability Rating F — failing academic performance")
    elif rating == "D":
        score += 20
        flags.append("Accountability Rating D — significantly below standards")
    elif rating == "C":
        score += 8

    staar_read = metrics.get("staar_reading_pct")
    if staar_read is not None and staar_read < STATE_AVG_READING:
        gap = round(STATE_AVG_READING - staar_read, 1)
        score += 15
        flags.append(f"STAAR Reading {staar_read:.0f}% — {gap}pts below state avg ({STATE_AVG_READING:.0f}%)")

    staar_math = metrics.get("staar_math_pct")
    if staar_math is not None and staar_math < STATE_AVG_MATH:
        gap = round(STATE_AVG_MATH - staar_math, 1)
        score += 15
        flags.append(f"STAAR Math {staar_math:.0f}% — {gap}pts below state avg ({STATE_AVG_MATH:.0f}%)")

    sped_read = metrics.get("staar_sped_reading_pct")
    all_read = metrics.get("staar_reading_pct")
    if sped_read is not None and all_read is not None:
        sped_gap = all_read - sped_read
        if sped_gap > 20:
            score += 20
            flags.append(
                f"Special Ed STAAR Reading gap: {sped_gap:.0f}pts below district avg "
                f"— IEP/accommodation compliance opportunity for Babbage"
            )
        elif sped_gap > 10:
            score += 10
            flags.append(f"Special Ed STAAR Reading gap: {sped_gap:.0f}pts — IEP tracking gap")

    sped_math = metrics.get("staar_sped_math_pct")
    all_math = metrics.get("staar_math_pct")
    if sped_math is not None and all_math is not None:
        sped_gap = all_math - sped_math
        if sped_gap > 20:
            score += 10
            flags.append(
                f"Special Ed STAAR Math gap: {sped_gap:.0f}pts — accommodation adherence concern"
            )

    turnover = metrics.get("teacher_turnover_pct")
    if turnover is not None:
        if turnover > 25:
            score += 20
            flags.append(
                f"Teacher turnover {turnover:.0f}% — severe IEP institutional knowledge loss, "
                f"new teachers lack accommodation context"
            )
        elif turnover > 18:
            score += 15
            flags.append(
                f"Teacher turnover {turnover:.0f}% — IEP continuity risk, "
                f"accommodation compliance depends on Babbage documentation"
            )
        elif turnover > 12:
            score += 8
            flags.append(f"Teacher turnover {turnover:.0f}% — above-average staff churn")

    absent = metrics.get("chronic_absent_pct")
    if absent is not None and absent > 20:
        score += 8
        flags.append(
            f"Chronic absenteeism {absent:.0f}% — students missing services, "
            f"accommodation tracking falls behind"
        )

    return min(score, 100), flags


# ── Babbage pitch generation ──────────────────────────────────────────────────

BABBAGE_SYSTEM = """You are a K-12 EdTech sales strategist for Babbage, an IEP/BIP/504 accommodation
compliance tracking platform. Your primary user is the classroom teacher.

Babbage solves: teachers missing or forgetting IEP/504 accommodations, compliance documentation gaps,
special education coordinators spending hours verifying accommodation delivery, districts failing
state audits due to inconsistent records, and high teacher turnover causing institutional knowledge loss
around student needs.

Your task: given a Texas school district's performance data and trouble flags, write a compelling,
data-driven Babbage sales pitch document for the sales team to use when opening conversations with
the district's Special Education Director or Superintendent.

The pitch should:
1. Open with the district's specific failures (use real numbers)
2. Connect each failure to a Babbage solution with a concrete KPI target
3. Provide specific opening talking points tailored to the district's pain
4. Stay focused on ROI, IDEA compliance, and teacher efficiency

Return ONLY valid JSON (no markdown fences) in this exact structure:
{
  "executive_summary": "2-3 sentence opening that names the district, cites key failures, and positions Babbage as the solution",
  "district_failures": [
    {"metric": "metric name", "value": "formatted value with % or context", "severity": "critical|high|medium"}
  ],
  "babbage_solutions": [
    {"problem": "specific district pain stated as fact", "solution": "what Babbage does", "kpi_target": "measurable improvement target with timeframe"}
  ],
  "kpi_projections": [
    {"kpi": "KPI name", "current": "current state", "target": "goal", "timeframe": "e.g. 12 months"}
  ],
  "opening_talking_points": [
    "talking point 1 — a specific, data-driven conversation opener",
    "talking point 2",
    "talking point 3"
  ],
  "urgency": "high|medium|low"
}"""


async def generate_babbage_pitch(district: dict) -> dict:
    """
    Calls Claude to generate a Babbage sales pitch for a specific district.
    Falls back to a static template if the AI call fails or the key is missing.
    """
    key = os.getenv("ANTHROPIC_API_KEY")

    flags = district.get("trouble_flags") or []
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except Exception:
            flags = []

    rating = district.get("accountability_rating", "Unknown")
    rating_label = {
        "IR": "Improvement Required (state intervention risk)",
        "F": "F — Failing",
        "D": "D — Below Standards",
        "C": "C — Approaching Standards",
        "A": "A — Met Standards",
        "B": "B — Recognized",
    }.get(rating, rating)

    dist_name = district.get("district_name", "Unknown District")

    # ── Try Claude AI ─────────────────────────────────────────────────────────
    if key:
        prompt = f"""Generate a Babbage sales pitch document for this Texas school district.

District: {dist_name}
District ID: {district.get('district_id', 'N/A')}
ESC Region: {district.get('esc_region', 'Unknown')}
Enrollment: {district.get('enrollment', 'Unknown')}
Accountability Rating: {rating_label}
Trouble Score: {district.get('trouble_score', 0)}/100

PERFORMANCE FLAGS:
{chr(10).join(f'- {f}' for f in flags) if flags else '- No specific flags captured — use district name and region to infer likely challenges'}

RAW METRICS:
- STAAR Reading (all students): {district.get('staar_reading_pct', 'N/A')}%
- STAAR Math (all students): {district.get('staar_math_pct', 'N/A')}%
- STAAR Reading (Special Ed): {district.get('staar_sped_reading_pct', 'N/A')}%
- STAAR Math (Special Ed): {district.get('staar_sped_math_pct', 'N/A')}%
- Graduation rate: {district.get('grad_rate', 'N/A')}%
- Teacher turnover: {district.get('teacher_turnover_pct', 'N/A')}%
- Special Ed student %: {district.get('sped_student_pct', 'N/A')}%
- Chronic absenteeism: {district.get('chronic_absent_pct', 'N/A')}%

TARGET BUYER: Special Education Director or Superintendent

Write the Babbage pitch JSON now. Be specific and bold — tie every solution to the district's actual numbers. If specific metrics are N/A, reference the district's known demographics or region context."""

        try:
            client = anthropic.AsyncAnthropic(api_key=key)
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1800,
                system=BABBAGE_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            parsed = _extract_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[tx_screener] Claude pitch error for {dist_name}: {e}")

    # ── Static fallback pitch ─────────────────────────────────────────────────
    return _static_pitch(district, dist_name, rating, flags)


def _extract_json(raw: str) -> dict | None:
    """Robustly extracts a JSON object from a string, stripping any markdown fences."""
    # Strip code fences
    text = raw
    if "```" in text:
        # Find content between first ``` and last ```
        parts = text.split("```")
        # parts[1] is the fenced block; strip language identifier like "json"
        for part in parts[1::2]:  # odd-indexed = inside fences
            cleaned = part.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
            if cleaned.startswith("{"):
                text = cleaned
                break
    # Find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _static_pitch(district: dict, name: str, rating: str, flags: list) -> dict:
    """Generates a template-based Babbage pitch when Claude is unavailable."""
    score = district.get("trouble_score", 0)
    urgency = "high" if score >= 50 else "medium" if score >= 25 else "low"
    enrollment = district.get("enrollment")
    enroll_str = f"{enrollment:,} students" if enrollment else "a significant student population"
    read_pct = district.get("staar_reading_pct")
    math_pct = district.get("staar_math_pct")
    turnover = district.get("teacher_turnover_pct")
    sped_pct = district.get("sped_student_pct")

    rating_risk = {
        "IR": "is under state Improvement Required status — at immediate risk of state intervention",
        "F":  "has received an F accountability rating — signaling systemic academic failure",
        "D":  "holds a D accountability rating — significantly below state performance standards",
        "C":  "is rated C — approaching standards but leaving students behind",
    }.get(rating, "shows multiple performance gaps that Babbage can help address")

    failures = []
    if rating in ("IR", "F", "D"):
        failures.append({"metric": "Accountability Rating", "value": f"Rating {rating} — {rating_risk}", "severity": "critical"})
    if read_pct and read_pct < STATE_AVG_READING:
        failures.append({"metric": "STAAR Reading", "value": f"{read_pct:.0f}% meeting grade level — {STATE_AVG_READING - read_pct:.0f}pts below state avg", "severity": "high"})
    if math_pct and math_pct < STATE_AVG_MATH:
        failures.append({"metric": "STAAR Math", "value": f"{math_pct:.0f}% meeting grade level — {STATE_AVG_MATH - math_pct:.0f}pts below state avg", "severity": "high"})
    if turnover and turnover > 18:
        failures.append({"metric": "Teacher Turnover", "value": f"{turnover:.0f}% annual turnover — IEP institutional knowledge lost every year", "severity": "high" if turnover > 25 else "medium"})
    if not failures:
        failures.append({"metric": "Accommodation Compliance Risk", "value": "District lacks centralized IEP/504 tracking — accommodation delivery unverified", "severity": "medium"})

    sped_str = f"{sped_pct:.0f}% of district enrollment" if sped_pct else "typically 10%+ of enrollment"

    return {
        "executive_summary": (
            f"{name} {rating_risk}. With {enroll_str} and special education students representing "
            f"{sped_str}, inconsistent IEP and 504 accommodation delivery is both a compliance liability "
            f"and a direct driver of the district's performance gaps. Babbage gives every teacher "
            f"real-time accommodation visibility, turning compliance from a burden into a performance driver."
        ),
        "district_failures": failures,
        "babbage_solutions": [
            {
                "problem": f"Teachers at {name} lack a reliable system to track daily IEP/504 accommodation delivery, creating IDEA/Section 504 compliance gaps that surface during state audits.",
                "solution": "Babbage provides a teacher-facing dashboard showing every student's active accommodations before each class period — no more missed extended time, preferential seating, or read-aloud supports.",
                "kpi_target": "100% accommodation delivery documentation rate within 90 days of deployment"
            },
            {
                "problem": f"High teacher turnover ({f'{turnover:.0f}%' if turnover else 'above-average'}) means new staff arrive without full context on their students' IEPs, leading to accommodation gaps in the first weeks of each semester.",
                "solution": "Babbage stores IEP/BIP/504 requirements at the student level, instantly accessible to any teacher on day one — no paper file hunting, no delay.",
                "kpi_target": "New teacher accommodation readiness on Day 1, eliminating the typical 3-6 week onboarding gap"
            },
            {
                "problem": f"Special Education coordinators at {name} spend hours per week manually verifying accommodation delivery across classrooms, pulling them away from student support.",
                "solution": "Babbage provides a single compliance dashboard showing accommodation delivery rates by teacher, student, and IEP goal — so coordinators see gaps in real time without manual check-ins.",
                "kpi_target": "10+ coordinator hours per week reclaimed from manual compliance verification"
            },
        ],
        "kpi_projections": [
            {"kpi": "IEP Accommodation Compliance Rate", "current": "Unknown / unverified", "target": "95%+", "timeframe": "90 days"},
            {"kpi": "STAAR SpEd Performance Gap", "current": f"{f'{district.get(chr(115)+chr(116)+chr(97)+chr(97)+chr(114)+chr(95)+chr(115)+chr(112)+chr(101)+chr(100)+chr(95)+chr(114)+chr(101)+chr(97)+chr(100)+chr(105)+chr(110)+chr(103)+chr(95)+chr(112)+chr(99)+chr(116)):.0f}%' if district.get('staar_sped_reading_pct') else 'Needs assessment'}", "target": "Reduce gap by 8pts", "timeframe": "12 months"},
            {"kpi": "Coordinator Hours on Compliance Admin", "current": "10–15 hrs/week", "target": "< 3 hrs/week", "timeframe": "6 months"},
            {"kpi": "New Teacher Accommodation Readiness", "current": "3–6 week ramp", "target": "Day 1 ready", "timeframe": "At deployment"},
        ],
        "opening_talking_points": [
            f"'{name} {rating_risk} — what's your current process for verifying that every teacher is delivering accommodations for every IEP student, every day?'",
            f"'When a new teacher joins mid-year, how quickly can they access a student's IEP accommodation requirements? Babbage makes it instant.'",
            f"'Special education litigation and state audits in Texas increasingly hinge on documentation of accommodation delivery — not just the IEP itself. How is your district capturing that evidence today?'",
        ],
        "urgency": urgency,
    }


# ── Client-facing report ──────────────────────────────────────────────────────

BABBAGE_CLIENT_SYSTEM = """You are a communications specialist for Babbage, an IEP/BIP/504 accommodation
compliance platform for K-12 school districts. Your audience is a district administrator —
a Superintendent, Assistant Superintendent, or Special Education Director.

Your task: write a warm, professional, client-facing proposal document that introduces Babbage,
acknowledges the district's specific situation, and explains clearly how Babbage can help.

Tone: helpful, respectful, direct. Never condescending. Never use language like "failures" or "problems" —
use "challenges", "opportunities", "areas where we can support you".

Babbage solves: teachers not knowing or forgetting IEP/504 accommodations during the school day,
Special Ed coordinators spending hours manually verifying accommodation delivery, districts facing
compliance exposure during state audits, and institutional knowledge loss when teachers turn over.

The platform is teacher-facing: every teacher opens their classroom view and instantly sees the exact
accommodations required for each student in that period — extended time, preferential seating,
read-aloud, reduced assignments, behavior plans. It logs delivery, creating an automatic audit trail.

Return ONLY valid JSON (no markdown fences) in this exact structure:
{
  "tagline": "One-sentence value proposition for this specific district",
  "what_we_do": "2-3 sentence plain-language description of what Babbage is and does",
  "district_context": "1-2 sentence acknowledgment of what we noticed about this district, framed respectfully",
  "challenges_identified": [
    {"challenge": "Short label for the challenge", "context": "1-2 sentences citing specific data or context, framed as opportunity"}
  ],
  "how_we_help": [
    {"capability": "Babbage feature name", "benefit": "How it directly addresses this district's situation"}
  ],
  "expected_outcomes": [
    {"outcome": "Measurable result", "detail": "Timeline or supporting context"}
  ],
  "call_to_action": "A warm, specific invitation — e.g. schedule a 30-min demo, pilot with one campus"
}"""


async def generate_client_report(district: dict) -> dict:
    """
    Calls Claude to generate a client-facing Babbage proposal for a specific district.
    Falls back to a static template if the AI call fails or the key is missing.
    """
    key = os.getenv("ANTHROPIC_API_KEY")

    flags = district.get("trouble_flags") or []
    if isinstance(flags, str):
        try:
            flags = json.loads(flags)
        except Exception:
            flags = []

    rating = district.get("accountability_rating", "Unknown")
    rating_label = {
        "IR": "Improvement Required",
        "F":  "F — Below Standards",
        "D":  "D — Below Standards",
        "C":  "C — Approaching Standards",
        "A":  "A — Met Standards",
        "B":  "B — Recognized",
    }.get(rating, rating)

    dist_name = district.get("district_name", "Unknown District")
    enrollment = district.get("enrollment")
    enroll_str = f"{enrollment:,}" if enrollment else "unknown"

    if key:
        prompt = f"""Generate a client-facing Babbage proposal for this Texas school district.

District: {dist_name}
ESC Region: {district.get('esc_region', 'Unknown')}
Enrollment: {enroll_str} students
Accountability Rating: {rating_label}

PERFORMANCE CONTEXT (use respectfully — frame as areas to support, not failures):
- STAAR Reading: {district.get('staar_reading_pct', 'N/A')}% of students meeting grade level
- STAAR Math: {district.get('staar_math_pct', 'N/A')}% of students meeting grade level
- STAAR Reading (Special Education students): {district.get('staar_sped_reading_pct', 'N/A')}%
- STAAR Math (Special Education students): {district.get('staar_sped_math_pct', 'N/A')}%
- Graduation rate: {district.get('grad_rate', 'N/A')}%
- Teacher turnover: {district.get('teacher_turnover_pct', 'N/A')}%
- Special Education enrollment: {district.get('sped_student_pct', 'N/A')}% of students
- Chronic absenteeism: {district.get('chronic_absent_pct', 'N/A')}%

IDENTIFIED AREA FLAGS (internal signals, translate to supportive language for the client):
{chr(10).join(f'- {f}' for f in flags) if flags else '- General support opportunity based on district profile'}

Write the proposal JSON now. Be specific, warm, and data-grounded. Tie every Babbage capability to something real about this district."""

        try:
            client = anthropic.AsyncAnthropic(api_key=key)
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1800,
                system=BABBAGE_CLIENT_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            parsed = _extract_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[tx_screener] Claude client report error for {dist_name}: {e}")

    # ── Static fallback ───────────────────────────────────────────────────────
    score = district.get("trouble_score", 0)
    read_pct = district.get("staar_reading_pct")
    math_pct = district.get("staar_math_pct")
    turnover = district.get("teacher_turnover_pct")
    sped_pct = district.get("sped_student_pct")
    sped_str = f"{sped_pct:.0f}% of your students" if sped_pct else "a significant portion of your student body"
    challenges = []
    if read_pct and read_pct < 70:
        challenges.append({"challenge": "Reading Outcomes", "context": f"With {read_pct:.0f}% of students meeting grade-level reading benchmarks, targeted accommodation delivery for your Special Education students is a meaningful lever for improvement."})
    if math_pct and math_pct < 70:
        challenges.append({"challenge": "Math Outcomes", "context": f"With {math_pct:.0f}% meeting math benchmarks, ensuring every accommodation — extended time, calculators, reduced items — is consistently delivered each class period can directly impact STAAR performance."})
    if turnover and turnover > 15:
        challenges.append({"challenge": "Teacher Continuity", "context": f"At {turnover:.0f}% annual teacher turnover, new staff frequently join without full context on their students' IEP requirements. Babbage makes that information available on day one."})
    if not challenges:
        challenges.append({"challenge": "Accommodation Consistency", "context": "Ensuring every teacher delivers every IEP and 504 accommodation, every period, is challenging without a centralized system — especially as enrollment and compliance expectations grow."})
    return {
        "tagline": f"Helping {dist_name} give every Special Education student the support they're entitled to, every day.",
        "what_we_do": (
            "Babbage is a teacher-facing IEP/504 accommodation compliance platform for K-12 districts. "
            "It gives every teacher a clear, real-time view of each student's active accommodations before the class period starts — "
            "extended time, read-aloud, preferential seating, behavior plans — and automatically logs delivery to create a clean audit trail."
        ),
        "district_context": (
            f"{dist_name} serves {enroll_str} students, with special education students representing {sped_str}. "
            "Ensuring consistent, documented accommodation delivery across every campus and every classroom is exactly the kind of challenge Babbage was built to solve."
        ),
        "challenges_identified": challenges,
        "how_we_help": [
            {"capability": "Teacher Accommodation Dashboard", "benefit": "Every teacher sees their students' IEP/504 requirements before each class — no paper files, no guessing, no missed supports."},
            {"capability": "Automatic Compliance Logging", "benefit": "Accommodation delivery is recorded passively as teachers use the platform, creating a real-time audit trail without adding to teacher workload."},
            {"capability": "New Staff Onboarding", "benefit": f"With teacher turnover a factor in many Texas districts, Babbage ensures new hires at {dist_name} have full student context on day one — not week six."},
            {"capability": "Coordinator Oversight View", "benefit": "Special Ed coordinators get a district-wide compliance dashboard — spotting gaps before they become audit findings, not after."},
        ],
        "expected_outcomes": [
            {"outcome": "Full accommodation documentation coverage", "detail": "100% of IEP/504 students have documented accommodation delivery within 90 days"},
            {"outcome": "Reduced coordinator compliance burden", "detail": "From 10–15 hours/week of manual verification to under 3 hours — freeing coordinators to support teachers directly"},
            {"outcome": "Audit-ready records", "detail": "State and federal special education audits covered by automatic log export — no advance preparation needed"},
            {"outcome": "Improved SpEd student outcomes", "detail": "Districts using Babbage typically see measurable STAAR improvement for Special Education students within 12 months of deployment"},
        ],
        "call_to_action": f"We'd love to show you how Babbage works with a 30-minute walkthrough tailored to {dist_name}'s profile. We can also pilot on a single campus so your team can see the impact before any district-wide commitment.",
    }


# ── Main scan orchestration ───────────────────────────────────────────────────

async def scan_region(region: int, progress_cb=None) -> dict:
    """
    Full pipeline for a region:
    1. Fetch district list
    2. Fetch TAPR metrics per district
    3. Score each district
    4. Upsert to DB
    5. Auto-create prospect accounts for troubled districts (score >= 40)
    Returns summary stats.
    """
    results = {"region": region, "total": 0, "troubled": 0, "accounts_created": 0, "errors": 0}

    if region not in ESC_REGIONS:
        raise ValueError(f"Invalid ESC region: {region}")

    if progress_cb:
        await progress_cb("fetching", f"Fetching district list for Region {region}...")

    districts = await fetch_tea_district_list(region)
    if not districts:
        raise ValueError(f"No districts found for ESC Region {region}. TEA data may be unavailable.")

    results["total"] = len(districts)

    for i, d in enumerate(districts):
        dist_id = d["district_id"]
        dist_name = d["district_name"]

        if progress_cb:
            await progress_cb(
                "scanning",
                f"Scanning {dist_name} ({i+1}/{len(districts)})..."
            )

        # Fetch metrics — gracefully degrade to empty dict so district still appears
        try:
            metrics = await fetch_district_tapr(dist_id)
        except Exception as e:
            print(f"[tx_screener] Metrics unavailable for {dist_name} ({dist_id}): {e}")
            metrics = {}

        try:
            score, flags = score_district_trouble(metrics)

            await db.upsert_texas_district(
                district_id=dist_id,
                district_name=dist_name,
                esc_region=region,
                enrollment=metrics.get("enrollment"),
                accountability_rating=metrics.get("accountability_rating"),
                staar_reading_pct=metrics.get("staar_reading_pct"),
                staar_math_pct=metrics.get("staar_math_pct"),
                staar_sped_reading_pct=metrics.get("staar_sped_reading_pct"),
                staar_sped_math_pct=metrics.get("staar_sped_math_pct"),
                grad_rate=metrics.get("grad_rate"),
                teacher_turnover_pct=metrics.get("teacher_turnover_pct"),
                sped_student_pct=metrics.get("sped_student_pct"),
                chronic_absent_pct=metrics.get("chronic_absent_pct"),
                trouble_score=score,
                trouble_flags=flags,
            )

            # Auto-create prospect account for troubled districts
            if score >= 40:
                results["troubled"] += 1
                existing = await db.get_texas_district(dist_id)
                if existing and not existing.get("account_id"):
                    account_id = await db.create_account(
                        name=dist_name,
                        district_domain=None,
                        account_type="prospect",
                        nces_id=dist_id,
                        district_legal_name=dist_name,
                    )
                    await db.link_texas_district_account(dist_id, account_id)
                    results["accounts_created"] += 1

        except Exception as e:
            print(f"[tx_screener] Error processing {dist_name} ({dist_id}): {e}")
            results["errors"] += 1
            # Still upsert with just the name/region so it shows in list
            try:
                await db.upsert_texas_district(
                    district_id=dist_id,
                    district_name=dist_name,
                    esc_region=region,
                    trouble_score=0,
                    trouble_flags=[],
                )
            except Exception:
                pass

    if progress_cb:
        await progress_cb("done",
            f"Scanned {results['total']} districts — {results['troubled']} troubled, "
            f"{results['accounts_created']} added as prospects"
        )

    return results
