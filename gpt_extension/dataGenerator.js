/**
 * Data Generator — Address & Personal Data
 * Countries: KR (South Korea), US (United States), IN (India)
 *
 * US addresses use 2-letter state codes (e.g. "NY", "CA")
 * to correctly fill Stripe's State dropdown.
 */

// ─── 🇰🇷 South Korea ─────────────────────────────────────────────────────────
const KOREAN_ADDRESSES = [
  { name: 'Kim Min-jun',    state: 'Seoul',           city: 'Mapo-gu',          line1: '12-3 Mangwon-dong',          postal: '04101' },
  { name: 'Lee Seo-yeon',   state: 'Seoul',           city: 'Yongsan-gu',       line1: '45-7 Itaewon-ro',            postal: '04349' },
  { name: 'Park Ji-ho',     state: 'Seoul',           city: 'Gangnam-gu',       line1: '218 Teheran-ro',             postal: '06141' },
  { name: 'Choi Ha-yun',    state: 'Seoul',           city: 'Nowon-gu',         line1: '67-2 Junggye-ro',            postal: '01750' },
  { name: 'Jung Seo-jun',   state: 'Seoul',           city: 'Seodaemun-gu',     line1: '33 Hongjimun-ro',            postal: '03717' },
  { name: 'Kang Ji-eun',   state: 'Busan',           city: 'Haeundae-gu',      line1: '98-1 Haeundaehaebyeon-ro',   postal: '48094' },
  { name: 'Cho Min-seo',    state: 'Busan',           city: 'Busanjin-gu',      line1: '451 Jungang-daero',          postal: '47296' },
  { name: 'Yoon Ji-woo',   state: 'Busan',           city: 'Nam-gu',           line1: '12-8 Daeyeon-dong',          postal: '48513' },
  { name: 'Jang Seo-jin',  state: 'Busan',           city: 'Suyeong-gu',       line1: '76 Gwangnam-ro',             postal: '48200' },
  { name: 'Lim Ha-eun',    state: 'Daegu',           city: 'Jung-gu',          line1: '23-4 Gongpyeong-ro',         postal: '41919' },
  { name: 'Han Min-ho',    state: 'Daegu',           city: 'Dalseo-gu',        line1: '389 Dalgubeol-daero',        postal: '42709' },
  { name: 'Oh Seo-woo',    state: 'Daegu',           city: 'Buk-gu',           line1: '156-3 Gongdan-ro',           postal: '41599' },
  { name: 'Seo Ji-min',    state: 'Incheon',         city: 'Namdong-gu',       line1: '34-9 Guwol-dong',            postal: '21565' },
  { name: 'Shin Min-ji',   state: 'Incheon',         city: 'Bupyeong-gu',      line1: '222 Bupyeong-daero',         postal: '21358' },
  { name: 'Kwon Ji-yoo',   state: 'Incheon',         city: 'Gyeyang-gu',       line1: '47-1 Gyeyang-daero',         postal: '21031' },
  { name: 'Hwang Jae-hyun',state: 'Gwangju',         city: 'Buk-gu',           line1: '88 Yongbong-ro',             postal: '61086' },
  { name: 'Ahn Seo-yun',   state: 'Gwangju',         city: 'Gwangsan-gu',      line1: '195-2 Chungjanheol-ro',      postal: '62396' },
  { name: 'Song Ji-hoon',  state: 'Daejeon',         city: 'Seo-gu Dunsan-dong', line1: '1973-3 Ga-gil',            postal: '35208' },
  { name: 'Jeon Min-woo',  state: 'Daejeon',         city: 'Yuseong-gu',       line1: '291 Daehak-ro',              postal: '34141' },
  { name: 'Hong Ji-yun',   state: 'Daejeon',         city: 'Dong-gu',          line1: '52-7 Daedeok-daero',         postal: '34886' },
  { name: 'Kim Seo-hyun',  state: 'Ulsan',           city: 'Nam-gu',           line1: '217-3 Samsan-ro',            postal: '44679' },
  { name: 'Lee Ji-soo',    state: 'Ulsan',           city: 'Jung-gu',          line1: '74 Haksam-ro',               postal: '44438' },
  { name: 'Park Min-young', state: 'Sejong',          city: 'Sejong',           line1: '2130 Hannuri-daero',         postal: '30151' },
  { name: 'Choi Soo-jin',  state: 'Gyeonggi-do',    city: 'Suwon',            line1: '88-12 Ingye-ro',             postal: '16226' },
  { name: 'Jung Da-eun',   state: 'Gyeonggi-do',    city: 'Seongnam',         line1: '167 Bundan-ro',              postal: '13590' },
  { name: 'Kang Joon-ho',  state: 'Gyeonggi-do',    city: 'Goyang',           line1: '294 Hosu-ro',                postal: '10408' },
  { name: 'Cho Yeon-ju',   state: 'Gyeonggi-do',    city: 'Yongin',           line1: '45-3 Hyeoksin-ro',           postal: '16890' },
  { name: 'Yoon Tae-yang', state: 'Gyeonggi-do',    city: 'Bucheon',          line1: '39 Gilju-ro',                postal: '14545' },
  { name: 'Jang Hye-jin',  state: 'Gyeonggi-do',    city: 'Ansan',            line1: '512 Jungang-daero',          postal: '15588' },
  { name: 'Lim Dong-hyun', state: 'Gyeonggi-do',    city: 'Anyang',           line1: '77-2 Pyeongchon-daero',      postal: '14054' },
  { name: 'Han Ye-jin',    state: 'Gyeonggi-do',    city: 'Gwangmyeong',      line1: '153 Cheolsan-ro',            postal: '14214' },
  { name: 'Oh Jun-seok',   state: 'Gyeonggi-do',    city: 'Pyeongtaek',       line1: '29 Pyeongtaek-ro',           postal: '17780' },
  { name: 'Seo Na-yeon',   state: 'Gangwon-do',     city: 'Chuncheon',        line1: '11-6 Jungang-ro',            postal: '24210' },
  { name: 'Shin Woo-jin',  state: 'Gangwon-do',     city: 'Wonju',            line1: '88 Munsak-ro',               postal: '26431' },
  { name: 'Kwon Bo-ra',    state: 'Gangwon-do',     city: 'Gangneung',        line1: '34-1 Haean-ro',              postal: '25564' },
  { name: 'Hwang Tae-min', state: 'Chungcheongbuk-do', city: 'Cheongju',     line1: '98 Usam-ro',                 postal: '28457' },
  { name: 'Ahn Ji-na',     state: 'Chungcheongbuk-do', city: 'Chungju',      line1: '201 Uam-ro',                 postal: '27437' },
  { name: 'Song Kyung-soo',state: 'Chungcheongnam-do', city: 'Cheonan',      line1: '77 Boryeong-ro',             postal: '31097' },
  { name: 'Jeon Hana',     state: 'Chungcheongnam-do', city: 'Asan',         line1: '45-3 Asan-daero',            postal: '31507' },
  { name: 'Hong Seung-min',state: 'Jeollabuk-do',   city: 'Jeonju',           line1: '68-2 Girin-daero',           postal: '54948' },
  { name: 'Kim Da-hyun',   state: 'Jeollabuk-do',   city: 'Iksan',            line1: '123 Iksan-daero',            postal: '54593' },
  { name: 'Lee Eun-ji',    state: 'Jeollanam-do',   city: 'Mokpo',            line1: '42 Haean-ro',                postal: '58647' },
  { name: 'Park Chan-woo', state: 'Jeollanam-do',   city: 'Yeosu',            line1: '114 Yeosu-ro',               postal: '59613' },
  { name: 'Choi Ga-young', state: 'Gyeongsangbuk-do', city: 'Pohang',         line1: '218 Jungheung-ro',           postal: '37583' },
  { name: 'Jung Hyun-woo', state: 'Gyeongsangbuk-do', city: 'Gyeongju',       line1: '88 Wonhyo-ro',              postal: '38115' },
  { name: 'Kang Seul-gi',  state: 'Gyeongsangbuk-do', city: 'Gumi',           line1: '56-4 Gongdan-ro',           postal: '39328' },
  { name: 'Cho Byung-chan',state: 'Gyeongsangnam-do', city: 'Changwon',       line1: '287 Changwon-daero',         postal: '51429' },
  { name: 'Yoon Soo-ah',   state: 'Gyeongsangnam-do', city: 'Jinju',          line1: '63 Jinju-daero',            postal: '52727' },
  { name: 'Jang In-young', state: 'Gyeongsangnam-do', city: 'Gimhae',         line1: '37-9 Gimhae-daero',         postal: '50932' },
  { name: 'Lim Sang-woo',  state: 'Jeju-do',        city: 'Jeju',             line1: '102 Noehyeong-ro',           postal: '63219' },
  { name: 'Han Ji-young',  state: 'Jeju-do',        city: 'Seogwipo',         line1: '74-2 Jungang-ro',            postal: '63595' }
];


// ─── 🇺🇸 United States ───────────────────────────────────────────────────────
// State field uses 2-letter codes to match Stripe's State <select> values
const USA_ADDRESSES = [
  { name: 'John Smith',          state: 'NY', city: 'New York',     line1: '123 Broadway',          postal: '10001' },
  { name: 'Michael Brown',       state: 'CA', city: 'Los Angeles',  line1: '456 Sunset Blvd',       postal: '90001' },
  { name: 'Sarah Davis',         state: 'TX', city: 'Houston',      line1: '789 Main St',           postal: '77001' },
  { name: 'James Wilson',        state: 'FL', city: 'Miami',        line1: '101 Ocean Dr',          postal: '33101' },
  { name: 'Emma Garcia',         state: 'IL', city: 'Chicago',      line1: '202 Michigan Ave',      postal: '60601' },
  { name: 'Robert Miller',       state: 'WA', city: 'Seattle',      line1: '303 Pine St',           postal: '98101' },
  { name: 'Linda Martinez',      state: 'AZ', city: 'Phoenix',      line1: '404 Palm Lane',         postal: '85001' },
  { name: 'William Taylor',      state: 'GA', city: 'Atlanta',      line1: '505 Peachtree St',      postal: '30301' },
  { name: 'Elizabeth Anderson',  state: 'MA', city: 'Boston',       line1: '606 Beacon St',         postal: '02101' },
  { name: 'David Thomas',        state: 'CO', city: 'Denver',       line1: '707 Aspen Way',         postal: '80201' },
  { name: 'Jessica White',       state: 'PA', city: 'Philadelphia', line1: '808 Market St',         postal: '19101' },
  { name: 'Christopher Harris',  state: 'OH', city: 'Columbus',     line1: '909 Broad St',          postal: '43201' },
  { name: 'Ashley Jackson',      state: 'NC', city: 'Charlotte',    line1: '111 Trade St',          postal: '28201' },
  { name: 'Matthew Lewis',       state: 'NV', city: 'Las Vegas',    line1: '222 Las Vegas Blvd',    postal: '89101' },
  { name: 'Amanda Clark',        state: 'OR', city: 'Portland',     line1: '333 NW 23rd Ave',       postal: '97201' },
  { name: 'Daniel Robinson',     state: 'MN', city: 'Minneapolis',  line1: '444 Nicollet Mall',     postal: '55401' },
  { name: 'Stephanie Walker',    state: 'MI', city: 'Detroit',      line1: '555 Woodward Ave',      postal: '48201' },
  { name: 'Joshua Hall',         state: 'TN', city: 'Nashville',    line1: '666 Broadway',          postal: '37201' },
  { name: 'Megan Allen',         state: 'VA', city: 'Richmond',     line1: '777 Main St',           postal: '23219' },
  { name: 'Andrew Young',        state: 'NJ', city: 'Newark',       line1: '888 Broad St',          postal: '07101' }
];

// ─── 🇮🇳 India ───────────────────────────────────────────────────────────────
const INDIA_ADDRESSES = [
  { name: 'Rahul Sharma',        state: 'Karnataka',    city: 'Bengaluru',  line1: '44/1, 5th Main Road, Jayanagar',      postal: '560041' },
  { name: 'Anjali Deshmukh',     state: 'Maharashtra',  city: 'Mumbai',     line1: '229, Raghunath Chambers, Opp Sion Hospital', postal: '400022' },
  { name: 'Vikram Singh',        state: 'Delhi',        city: 'New Delhi',  line1: '7, Veer Savarkar Block, Shakarpur',   postal: '110092' },
  { name: 'Priyanka Chatterjee', state: 'West Bengal',  city: 'Kolkata',    line1: '12/A, Lake View Enclave, Gariahat Road', postal: '700029' },
  { name: 'Amit Patel',          state: 'Gujarat',      city: 'Vadodara',   line1: 'Opp. Nehru Bhavan, Rajmahal Road',   postal: '390001' },
  { name: 'Sanjay Gupta',        state: 'Uttar Pradesh',city: 'Lucknow',    line1: '14/2, Gomti Nagar, Near Marine Drive', postal: '226010' },
  { name: 'Deepa Rao',           state: 'Tamil Nadu',   city: 'Chennai',    line1: '56, Anna Salai, Mount Road',          postal: '600002' },
  { name: 'Rajesh Kumar',        state: 'Punjab',       city: 'Chandigarh', line1: 'Sector 17, SCO 45-46',               postal: '160017' },
  { name: 'Pooja Mehta',         state: 'Rajasthan',    city: 'Jaipur',     line1: '12 MI Road, Near Ajmeri Gate',       postal: '302001' },
  { name: 'Arjun Nair',          state: 'Kerala',       city: 'Kochi',      line1: '34 MG Road, Ernakulam',              postal: '682016' }
];

// ─── COUNTRY MAP ──────────────────────────────────────────────────────────────
const COUNTRY_MAP = {
  KR: { list: KOREAN_ADDRESSES, name: 'South Korea' },
  US: { list: USA_ADDRESSES,    name: 'United States' },
  IN: { list: INDIA_ADDRESSES,  name: 'India' }
};

/**
 * Get a random address by country code.
 * @param {string} countryCode — 'KR' | 'US' | 'IN'
 */
function getRandomAddress(countryCode = 'KR') {
  const entry = COUNTRY_MAP[countryCode] || COUNTRY_MAP.KR;
  const list  = entry.list;
  const addr  = list[Math.floor(Math.random() * list.length)];
  return {
    name:    addr.name,
    state:   addr.state,
    city:    addr.city,
    line1:   addr.line1,
    line2:   '',
    postal:  addr.postal,
    country: entry.name
  };
}

function getRandomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

const DataGeneratorAPI = {
  getRandomAddress,
  getRandomItem,
  KOREAN_ADDRESSES,
  USA_ADDRESSES,
  INDIA_ADDRESSES
};

if (typeof window !== 'undefined')                              window.DataGenerator = DataGeneratorAPI;
if (typeof self !== 'undefined' && typeof window === 'undefined') self.DataGenerator = DataGeneratorAPI;
if (typeof module !== 'undefined' && module.exports)           module.exports = DataGeneratorAPI;