document.addEventListener('DOMContentLoaded',()=>{
 const menu=document.querySelector('.menu-button'),nav=document.querySelector('.nav');
 if(menu&&nav){
  menu.addEventListener('click',()=>{
   const open=nav.classList.toggle('open');
   menu.setAttribute('aria-expanded',String(open));
   menu.textContent=open?'Закрыть':'Меню';
  });
  nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
   nav.classList.remove('open');menu.setAttribute('aria-expanded','false');menu.textContent='Меню';
  }));
 }
 const body=document.getElementById('chat-body'),choices=document.getElementById('chat-choices');
 if(!body||!choices)return;
 const replies={
  start:'Здравствуйте. Это демонстрация будущего помощника. Я могу показать, как будет устроена навигация по сайту и связь с Владимиром. Сейчас сообщения никуда не отправляются.',
  first:'Ознакомительная консультация бесплатна. На ней можно рассказать, что происходит, и понять, какая помощь нужна. Она ни к чему не обязывает. Отдельная первая платная консультация длится 60 минут.',
  work:'Владимир помогает разобраться с проблемой употребления алкоголя, мотивацией, триггерами и способами поддерживать трезвость. Работа индивидуальная. Он не ставит медицинских диагнозов и не назначает лекарства.',
  prices:'Первая платная консультация — 60 минут: 60 € или 5 000 ₽. Последующая — 50 минут: 50 € или 4 500 ₽. Короткая поддерживающая — 30–40 минут: 40 € или 3 500 ₽. Ознакомительная встреча бесплатна.',
  aa:'АА — важная часть личного опыта Владимира и один из ресурсов, которые он рекомендует. Профессиональная консультация не является спонсорством. Отказ от АА не мешает работе с консультантом.',
  contact:'С Владимиром можно связаться через WhatsApp или Telegram по номеру +358 46 617 0891, через MAX по номеру +7 981 188 1562 или по e-mail eglvlad2025@outlook.com. Все эти контакты на сайте открываются по прямым ссылкам. Передача контакта через самого бота пока не подключена.',
  urgent:'Если есть судороги, галлюцинации, сильная спутанность, признаки делирия, тяжёлая абстиненция или непосредственная опасность для жизни — обратитесь за местной экстренной медицинской помощью. Этот бот не является экстренной службой. При длительном тяжёлом употреблении резкая отмена алкоголя может быть опасной; безопасный порядок прекращения употребления необходимо обсудить с врачом.'
 };
 const labels={first:'Первая встреча',work:'Как проходит работа',prices:'Стоимость',aa:'АА и консультация',contact:'Связаться с Владимиром',urgent:'Нужна срочная помощь'};
 function add(text,user=false){
  const el=document.createElement('div');el.className='bubble'+(user?' user':'');el.textContent=text;
  body.appendChild(el);body.scrollTop=body.scrollHeight;
 }
 add(replies.start);
 Object.entries(labels).forEach(([key,label])=>{
  const b=document.createElement('button');b.className='choice';b.type='button';b.textContent=label;
  b.addEventListener('click',()=>{add(label,true);add(replies[key]);});
  choices.appendChild(b);
 });
});
document.addEventListener('DOMContentLoaded',()=>{const b=document.querySelector('.exact-menu-button'),n=document.querySelector('.exact-mobile-nav');if(b&&n){b.addEventListener('click',()=>{const open=n.classList.toggle('open');b.setAttribute('aria-expanded',String(open));b.textContent=open?'Закрыть':'Меню';});}});