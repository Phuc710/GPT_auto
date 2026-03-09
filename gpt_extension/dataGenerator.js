/**
 * Data Generator - Random address and personal data generation
 * Supports US and Korean addresses
 */

// US States and cities
const US_STATES = {
  'Alabama': ['Birmingham', 'Montgomery', 'Mobile', 'Huntsville'],
  'Alaska': ['Anchorage', 'Fairbanks', 'Juneau', 'Sitka'],
  'Arizona': ['Phoenix', 'Tucson', 'Mesa', 'Chandler'],
  'Arkansas': ['Little Rock', 'Fort Smith', 'Fayetteville', 'Springdale'],
  'California': ['Los Angeles', 'San Diego', 'San Jose', 'San Francisco', 'Fresno', 'Sacramento'],
  'Colorado': ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins'],
  'Connecticut': ['Bridgeport', 'New Haven', 'Hartford', 'Stamford'],
  'Delaware': ['Wilmington', 'Dover', 'Newark'],
  'Florida': ['Jacksonville', 'Miami', 'Tampa', 'Orlando', 'St. Petersburg'],
  'Georgia': ['Atlanta', 'Augusta', 'Columbus', 'Macon', 'Savannah'],
  'Hawaii': ['Honolulu', 'Pearl City', 'Hilo', 'Kailua'],
  'Idaho': ['Boise', 'Nampa', 'Meridian', 'Idaho Falls'],
  'Illinois': ['Chicago', 'Aurora', 'Rockford', 'Joliet', 'Naperville'],
  'Indiana': ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend'],
  'Iowa': ['Des Moines', 'Cedar Rapids', 'Davenport', 'Sioux City'],
  'Kansas': ['Wichita', 'Overland Park', 'Kansas City', 'Topeka'],
  'Kentucky': ['Louisville', 'Lexington', 'Bowling Green', 'Owensboro'],
  'Louisiana': ['New Orleans', 'Baton Rouge', 'Shreveport', 'Metairie'],
  'Maine': ['Portland', 'Lewiston', 'Bangor'],
  'Maryland': ['Baltimore', 'Frederick', 'Rockville', 'Gaithersburg'],
  'Massachusetts': ['Boston', 'Worcester', 'Springfield', 'Lowell', 'Cambridge'],
  'Michigan': ['Detroit', 'Grand Rapids', 'Warren', 'Sterling Heights'],
  'Minnesota': ['Minneapolis', 'Saint Paul', 'Rochester', 'Duluth'],
  'Mississippi': ['Jackson', 'Gulfport', 'Southaven', 'Hattiesburg'],
  'Missouri': ['Kansas City', 'Saint Louis', 'Springfield', 'Independence'],
  'Montana': ['Billings', 'Missoula', 'Great Falls', 'Bozeman'],
  'Nebraska': ['Omaha', 'Lincoln', 'Bellevue', 'Grand Island'],
  'Nevada': ['Las Vegas', 'Henderson', 'Reno', 'North Las Vegas'],
  'New Hampshire': ['Manchester', 'Nashua', 'Concord'],
  'New Jersey': ['Newark', 'Jersey City', 'Paterson', 'Elizabeth'],
  'New Mexico': ['Albuquerque', 'Las Cruces', 'Rio Rancho', 'Santa Fe'],
  'New York': ['New York', 'Buffalo', 'Rochester', 'Yonkers', 'Syracuse'],
  'North Carolina': ['Charlotte', 'Raleigh', 'Greensboro', 'Winston-Salem'],
  'North Dakota': ['Fargo', 'Bismarck', 'Grand Forks', 'Minot'],
  'Ohio': ['Columbus', 'Cleveland', 'Cincinnati', 'Toledo'],
  'Oklahoma': ['Oklahoma City', 'Tulsa', 'Norman', 'Broken Arrow'],
  'Oregon': ['Portland', 'Salem', 'Eugene', 'Oregon City'],
  'Pennsylvania': ['Philadelphia', 'Pittsburgh', 'Allentown', 'Erie'],
  'Rhode Island': ['Providence', 'Warwick', 'Cranston'],
  'South Carolina': ['Charleston', 'Columbia', 'North Charleston', 'Mount Pleasant'],
  'South Dakota': ['Sioux Falls', 'Rapid City', 'Aberdeen'],
  'Tennessee': ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga'],
  'Texas': ['Houston', 'San Antonio', 'Dallas', 'Austin', 'Fort Worth', 'El Paso'],
  'Utah': ['Salt Lake City', 'West Valley City', 'Provo', 'West Jordan'],
  'Vermont': ['Burlington', 'Essex', 'Rutland'],
  'Virginia': ['Virginia Beach', 'Norfolk', 'Chesapeake', 'Arlington', 'Richmond'],
  'Washington': ['Seattle', 'Spokane', 'Tacoma', 'Vancouver'],
  'West Virginia': ['Charleston', 'Huntington', 'Parkersburg'],
  'Wisconsin': ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha'],
  'Wyoming': ['Cheyenne', 'Casper', 'Laramie']
};

// Korean provinces and cities
const KOREAN_PROVINCES = {
  'Seoul': ['Seoul'],
  'Busan': ['Busan', 'Busanjin-gu', 'Dongnae-gu', 'Geumjeong-gu', 'Gijang-gun'],
  'Daegu': ['Daegu', 'Dalseo-gu', 'Dalseong-gun', 'Dong-gu', 'Jung-gu'],
  'Incheon': ['Incheon', 'Bupyeong-gu', 'Gyeyang-gu', 'Michuhol-gu'],
  'Gwangju': ['Gwangju', 'Buk-gu', 'Dong-gu', 'Gwangsan-gu', 'Nam-gu'],
  'Daejeon': ['Daejeon', 'Daedeok-gu', 'Dong-gu', 'Jung-gu', 'Seo-gu', 'Yuseong-gu'],
  'Ulsan': ['Ulsan', 'Dong-gu', 'Jung-gu', 'Nam-gu', 'Ulju-gun'],
  'Sejong': ['Sejong'],
  'Gyeonggi-do': ['Suwon', 'Seongnam', 'Goyang', 'Yongin', 'Bucheon', 'Ansan', 'Anyang', 'Gwangmyeong', 'Pyeongtaek', 'Siheung'],
  'Gangwon-do': ['Chuncheon', 'Wonju', 'Gangneung', 'Donghae', 'Taebaek'],
  'Chungcheongbuk-do': ['Cheongju', 'Chungju', 'Jecheon', 'Eumseong'],
  'Chungcheongnam-do': ['Cheonan', 'Asan', 'Seosan', 'Gongju', 'Boryeong'],
  'Jeollabuk-do': ['Jeonju', 'Iksan', 'Gunsan', 'Jeongeup', 'Namwon'],
  'Jeollanam-do': ['Mokpo', 'Yeosu', 'Suncheon', 'Gwangyang', 'Najin'],
  'Gyeongsangbuk-do': ['Daegu', 'Pohang', 'Gyeongju', 'Gumi', 'Yeongcheon'],
  'Gyeongsangnam-do': ['Changwon', 'Jinju', 'Tongyeong', 'Sacheon', 'Gimhae'],
  'Jeju-do': ['Jeju', 'Seogwipo']
};

// Common Korean names
const KOREAN_NAMES = {
  first: ['Kim', 'Lee', 'Park', 'Choi', 'Jung', 'Kang', 'Cho', 'Yoon', 'Jang', 'Lim', 'Han', 'Oh', 'Seo', 'Shin', 'Kwon', 'Hwang', 'Ahn', 'Song', 'Jeon', 'Hong'],
  last: ['Min-jun', 'Seo-jun', 'Jae-hyun', 'Ji-ho', 'Min-seo', 'Ha-yun', 'Ji-yoo', 'Seo-yeon', 'Ji-eun', 'Min-ji', 'Ha-eun', 'Ji-min', 'Seo-jin', 'Ji-hoon', 'Min-ho', 'Seo-woo', 'Ji-woo', 'Min-woo', 'Seo-yun', 'Ji-yun']
};

// Common US names
const US_NAMES = {
  first: ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Margaret', 'Thomas', 'Dorothy', 'Charles', 'Lisa'],
  last: ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin']
};

// Street name generators
const STREET_TYPES = ['Street', 'Avenue', 'Road', 'Boulevard', 'Drive', 'Lane', 'Way', 'Place', 'Court', 'Circle'];
const STREET_NAMES = ['Main', 'Oak', 'Pine', 'Maple', 'Cedar', 'Elm', 'Washington', 'Lincoln', 'Jefferson', 'Adams', 'Madison', 'Monroe', 'Jackson', 'Grant', 'Cleveland', 'Harrison', 'McKinley', 'Roosevelt', 'Kennedy', 'Johnson'];

/**
 * Generate random US address
 * @param {string} preferredState - Preferred state (optional)
 * @returns {object} Address object
 */
function generateUSAddress(preferredState = null) {
  const state = preferredState || getRandomItem(Object.keys(US_STATES));
  const city = getRandomItem(US_STATES[state]);
  const streetNumber = Math.floor(Math.random() * 9999) + 1;
  const streetName = getRandomItem(STREET_NAMES);
  const streetType = getRandomItem(STREET_TYPES);
  const zipCode = generateUSZipCode(state);
  
  const firstName = getRandomItem(US_NAMES.first);
  const lastName = getRandomItem(US_NAMES.last);
  
  return {
    name: `${firstName} ${lastName}`,
    address: `${streetNumber} ${streetName} ${streetType}`,
    city: city,
    state: state,
    zipCode: zipCode,
    country: 'US',
    fullAddress: `${streetNumber} ${streetName} ${streetType}, ${city}, ${state} ${zipCode}`
  };
}

/**
 * Generate random Korean address
 * @param {string} preferredProvince - Preferred province (optional)
 * @returns {object} Address object
 */
function generateKoreanAddress(preferredProvince = null) {
  const province = preferredProvince || getRandomItem(Object.keys(KOREAN_PROVINCES));
  const city = getRandomItem(KOREAN_PROVINCES[province]);
  const streetNumber = Math.floor(Math.random() * 999) + 1;
  const buildingNumber = Math.floor(Math.random() * 999) + 1;
  const zipCode = generateKoreanZipCode();
  
  const firstName = getRandomItem(KOREAN_NAMES.first);
  const lastName = getRandomItem(KOREAN_NAMES.last);
  
  return {
    name: `${firstName} ${lastName}`,
    address: `${streetNumber}-${buildingNumber}, ${city}`,
    city: city,
    province: province,
    zipCode: zipCode,
    country: 'KR',
    fullAddress: `${streetNumber}-${buildingNumber}, ${city}, ${province} ${zipCode}`
  };
}

/**
 * Generate US zip code
 * @param {string} state - State name
 * @returns {string} 5-digit zip code
 */
function generateUSZipCode(state) {
  // Simple zip code generation based on state
  const stateCodes = {
    'Alabama': '35', 'Alaska': '99', 'Arizona': '85', 'Arkansas': '72',
    'California': '90', 'Colorado': '80', 'Connecticut': '06', 'Delaware': '19',
    'Florida': '32', 'Georgia': '30', 'Hawaii': '96', 'Idaho': '83',
    'Illinois': '60', 'Indiana': '46', 'Iowa': '50', 'Kansas': '66',
    'Kentucky': '40', 'Louisiana': '70', 'Maine': '04', 'Maryland': '20',
    'Massachusetts': '02', 'Michigan': '48', 'Minnesota': '55', 'Mississippi': '39',
    'Missouri': '63', 'Montana': '59', 'Nebraska': '68', 'Nevada': '89',
    'New Hampshire': '03', 'New Jersey': '07', 'New Mexico': '87', 'New York': '10',
    'North Carolina': '27', 'North Dakota': '58', 'Ohio': '43', 'Oklahoma': '73',
    'Oregon': '97', 'Pennsylvania': '15', 'Rhode Island': '02', 'South Carolina': '29',
    'South Dakota': '57', 'Tennessee': '37', 'Texas': '75', 'Utah': '84',
    'Vermont': '05', 'Virginia': '22', 'Washington': '98', 'West Virginia': '25',
    'Wisconsin': '53', 'Wyoming': '82'
  };
  
  const prefix = stateCodes[state] || '00';
  const suffix = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
  return prefix + suffix.substring(0, 3);
}

/**
 * Generate Korean zip code
 * @returns {string} 5-digit zip code
 */
function generateKoreanZipCode() {
  // Korean zip codes are 5 digits
  return Math.floor(Math.random() * 90000 + 10000).toString();
}

/**
 * Generate random email
 * @param {string} name - Person's name
 * @returns {string} Email address
 */
function generateEmail(name) {
  const domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com'];
  const cleanName = name.toLowerCase().replace(/\s+/g, '').replace(/[^a-z]/g, '');
  const randomNum = Math.floor(Math.random() * 999) + 1;
  const domain = getRandomItem(domains);
  return `${cleanName}${randomNum}@${domain}`;
}

/**
 * Generate random phone number
 * @param {string} country - Country code (US or KR)
 * @returns {string} Phone number
 */
function generatePhoneNumber(country = 'US') {
  if (country === 'KR') {
    // Korean format: 010-XXXX-XXXX
    const part1 = '010';
    const part2 = Math.floor(Math.random() * 9000 + 1000);
    const part3 = Math.floor(Math.random() * 9000 + 1000);
    return `${part1}-${part2}-${part3}`;
  } else {
    // US format: (XXX) XXX-XXXX
    const areaCode = Math.floor(Math.random() * 900 + 100);
    const part1 = Math.floor(Math.random() * 900 + 100);
    const part2 = Math.floor(Math.random() * 9000 + 1000);
    return `(${areaCode}) ${part1}-${part2}`;
  }
}

/**
 * Generate complete random data set
 * @param {string} country - Country (US or KR)
 * @param {string} preferredState - Preferred state/province
 * @returns {object} Complete data set
 */
function generateRandomData(country = 'US', preferredState = null) {
  let address;
  
  if (country === 'KR') {
    address = generateKoreanAddress(preferredState);
  } else {
    address = generateUSAddress(preferredState);
  }
  
  return {
    ...address,
    email: generateEmail(address.name),
    phone: generatePhoneNumber(country)
  };
}

/**
 * Get random item from array
 * @param {array} array - Array to pick from
 * @returns {*} Random item
 */
function getRandomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    generateUSAddress,
    generateKoreanAddress,
    generateEmail,
    generatePhoneNumber,
    generateRandomData,
    US_STATES,
    KOREAN_PROVINCES
  };
}

// Browser/Extension context
if (typeof window !== 'undefined') {
  window.DataGenerator = {
    generateUSAddress,
    generateKoreanAddress,
    generateEmail,
    generatePhoneNumber,
    generateRandomData,
    US_STATES,
    KOREAN_PROVINCES
  };
}

// Service Worker context
if (typeof self !== 'undefined' && typeof window === 'undefined') {
  self.DataGenerator = {
    generateUSAddress,
    generateKoreanAddress,
    generateEmail,
    generatePhoneNumber,
    generateRandomData,
    US_STATES,
    KOREAN_PROVINCES
  };
}