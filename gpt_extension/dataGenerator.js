/**
 * Data Generator - Korean address and personal data generation
 * 50 real Korean addresses for random selection
 */

// 50 real Korean addresses with name, state, city, address, postal
const KOREAN_ADDRESSES = [
  { name: 'Kim Min-jun', state: 'Seoul', city: 'Mapo-gu', line1: '12-3 Mangwon-dong', postal: '04101' },
  { name: 'Lee Seo-yeon', state: 'Seoul', city: 'Yongsan-gu', line1: '45-7 Itaewon-ro', postal: '04349' },
  { name: 'Park Ji-ho', state: 'Seoul', city: 'Gangnam-gu', line1: '218 Teheran-ro', postal: '06141' },
  { name: 'Choi Ha-yun', state: 'Seoul', city: 'Nowon-gu', line1: '67-2 Junggye-ro', postal: '01750' },
  { name: 'Jung Seo-jun', state: 'Seoul', city: 'Seodaemun-gu', line1: '33 Hongjimun-ro', postal: '03717' },
  { name: 'Kang Ji-eun', state: 'Busan', city: 'Haeundae-gu', line1: '98-1 Haeundaehaebyeon-ro', postal: '48094' },
  { name: 'Cho Min-seo', state: 'Busan', city: 'Busanjin-gu', line1: '451 Jungang-daero', postal: '47296' },
  { name: 'Yoon Ji-woo', state: 'Busan', city: 'Nam-gu', line1: '12-8 Daeyeon-dong', postal: '48513' },
  { name: 'Jang Seo-jin', state: 'Busan', city: 'Suyeong-gu', line1: '76 Gwangnam-ro', postal: '48200' },
  { name: 'Lim Ha-eun', state: 'Daegu', city: 'Jung-gu', line1: '23-4 Gongpyeong-ro', postal: '41919' },
  { name: 'Han Min-ho', state: 'Daegu', city: 'Dalseo-gu', line1: '389 Dalgubeol-daero', postal: '42709' },
  { name: 'Oh Seo-woo', state: 'Daegu', city: 'Buk-gu', line1: '156-3 Gongdan-ro', postal: '41599' },
  { name: 'Seo Ji-min', state: 'Incheon', city: 'Namdong-gu', line1: '34-9 Guwol-dong', postal: '21565' },
  { name: 'Shin Min-ji', state: 'Incheon', city: 'Bupyeong-gu', line1: '222 Bupyeong-daero', postal: '21358' },
  { name: 'Kwon Ji-yoo', state: 'Incheon', city: 'Gyeyang-gu', line1: '47-1 Gyeyang-daero', postal: '21031' },
  { name: 'Hwang Jae-hyun', state: 'Gwangju', city: 'Buk-gu', line1: '88 Yongbong-ro', postal: '61086' },
  { name: 'Ahn Seo-yun', state: 'Gwangju', city: 'Gwangsan-gu', line1: '195-2 Chungjanheol-ro', postal: '62396' },
  { name: 'Song Ji-hoon', state: 'Daejeon', city: 'Seo-gu Dunsan-dong', line1: '1973-3 Ga-gil', postal: '35208' },
  { name: 'Jeon Min-woo', state: 'Daejeon', city: 'Yuseong-gu', line1: '291 Daehak-ro', postal: '34141' },
  { name: 'Hong Ji-yun', state: 'Daejeon', city: 'Dong-gu', line1: '52-7 Daedeok-daero', postal: '34886' },
  { name: 'Kim Seo-hyun', state: 'Ulsan', city: 'Nam-gu', line1: '217-3 Samsan-ro', postal: '44679' },
  { name: 'Lee Ji-soo', state: 'Ulsan', city: 'Jung-gu', line1: '74 Haksam-ro', postal: '44438' },
  { name: 'Park Min-young', state: 'Sejong', city: 'Sejong', line1: '2130 Hannuri-daero', postal: '30151' },
  { name: 'Choi Soo-jin', state: 'Gyeonggi-do', city: 'Suwon', line1: '88-12 Ingye-ro', postal: '16226' },
  { name: 'Jung Da-eun', state: 'Gyeonggi-do', city: 'Seongnam', line1: '167 Bundan-ro', postal: '13590' },
  { name: 'Kang Joon-ho', state: 'Gyeonggi-do', city: 'Goyang', line1: '294 Hosu-ro', postal: '10408' },
  { name: 'Cho Yeon-ju', state: 'Gyeonggi-do', city: 'Yongin', line1: '45-3 Hyeoksin-ro', postal: '16890' },
  { name: 'Yoon Tae-yang', state: 'Gyeonggi-do', city: 'Bucheon', line1: '39 Gilju-ro', postal: '14545' },
  { name: 'Jang Hye-jin', state: 'Gyeonggi-do', city: 'Ansan', line1: '512 Jungang-daero', postal: '15588' },
  { name: 'Lim Dong-hyun', state: 'Gyeonggi-do', city: 'Anyang', line1: '77-2 Pyeongchon-daero', postal: '14054' },
  { name: 'Han Ye-jin', state: 'Gyeonggi-do', city: 'Gwangmyeong', line1: '153 Cheolsan-ro', postal: '14214' },
  { name: 'Oh Jun-seok', state: 'Gyeonggi-do', city: 'Pyeongtaek', line1: '29 Pyeongtaek-ro', postal: '17780' },
  { name: 'Seo Na-yeon', state: 'Gangwon-do', city: 'Chuncheon', line1: '11-6 Jungang-ro', postal: '24210' },
  { name: 'Shin Woo-jin', state: 'Gangwon-do', city: 'Wonju', line1: '88 Munsak-ro', postal: '26431' },
  { name: 'Kwon Bo-ra', state: 'Gangwon-do', city: 'Gangneung', line1: '34-1 Haean-ro', postal: '25564' },
  { name: 'Hwang Tae-min', state: 'Chungcheongbuk-do', city: 'Cheongju', line1: '98 Usam-ro', postal: '28457' },
  { name: 'Ahn Ji-na', state: 'Chungcheongbuk-do', city: 'Chungju', line1: '201 Uam-ro', postal: '27437' },
  { name: 'Song Kyung-soo', state: 'Chungcheongnam-do', city: 'Cheonan', line1: '77 Boryeong-ro', postal: '31097' },
  { name: 'Jeon Hana', state: 'Chungcheongnam-do', city: 'Asan', line1: '45-3 Asan-daero', postal: '31507' },
  { name: 'Hong Seung-min', state: 'Jeollabuk-do', city: 'Jeonju', line1: '68-2 Girin-daero', postal: '54948' },
  { name: 'Kim Da-hyun', state: 'Jeollabuk-do', city: 'Iksan', line1: '123 Iksan-daero', postal: '54593' },
  { name: 'Lee Eun-ji', state: 'Jeollanam-do', city: 'Mokpo', line1: '42 Haean-ro', postal: '58647' },
  { name: 'Park Chan-woo', state: 'Jeollanam-do', city: 'Yeosu', line1: '114 Yeosu-ro', postal: '59613' },
  { name: 'Choi Ga-young', state: 'Gyeongsangbuk-do', city: 'Pohang', line1: '218 Jungheung-ro', postal: '37583' },
  { name: 'Jung Hyun-woo', state: 'Gyeongsangbuk-do', city: 'Gyeongju', line1: '88 Wonhyo-ro', postal: '38115' },
  { name: 'Kang Seul-gi', state: 'Gyeongsangbuk-do', city: 'Gumi', line1: '56-4 Gongdan-ro', postal: '39328' },
  { name: 'Cho Byung-chan', state: 'Gyeongsangnam-do', city: 'Changwon', line1: '287 Changwon-daero', postal: '51429' },
  { name: 'Yoon Soo-ah', state: 'Gyeongsangnam-do', city: 'Jinju', line1: '63 Jinju-daero', postal: '52727' },
  { name: 'Jang In-young', state: 'Gyeongsangnam-do', city: 'Gimhae', line1: '37-9 Gimhae-daero', postal: '50932' },
  { name: 'Lim Sang-woo', state: 'Jeju-do', city: 'Jeju', line1: '102 Noehyeong-ro', postal: '63219' },
  { name: 'Han Ji-young', state: 'Jeju-do', city: 'Seogwipo', line1: '74-2 Jungang-ro', postal: '63595' }
];

/**
 * Get a random Korean address from the preset list
 * @returns {object} Address object compatible with fill payload
 */
function getRandomKoreanAddress() {
  const addr = KOREAN_ADDRESSES[Math.floor(Math.random() * KOREAN_ADDRESSES.length)];
  return {
    name: addr.name,
    state: addr.state,
    city: addr.city,
    line1: addr.line1,
    line2: '',
    postal: addr.postal
  };
}

/**
 * Get random item from array
 */
function getRandomItem(array) {
  return array[Math.floor(Math.random() * array.length)];
}

// Export — browser/extension context
if (typeof window !== 'undefined') {
  window.DataGenerator = {
    getRandomKoreanAddress,
    KOREAN_ADDRESSES,
    getRandomItem
  };
}

// Service Worker context
if (typeof self !== 'undefined' && typeof window === 'undefined') {
  self.DataGenerator = {
    getRandomKoreanAddress,
    KOREAN_ADDRESSES,
    getRandomItem
  };
}

// Node context
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    getRandomKoreanAddress,
    KOREAN_ADDRESSES,
    getRandomItem
  };
}