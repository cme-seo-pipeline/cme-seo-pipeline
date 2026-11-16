(function(){
'use strict';
var API='https://cme-tracking-api-217943559750.europe-west1.run.app';

// Un comparateur peut apparaitre plusieurs fois sur la meme page (rare mais
// deja gere nativement par le plugin -- chaque shortcode genere son propre
// UID/nonce) : le code existant (ci-dessous, inchange) est donc transforme
// en fonction reutilisable plutot que d etre execute une seule fois au
// chargement du fichier -- UID/EDEF/CMPNONCE/CMPAJAX redeviennent des
// parametres au lieu de constantes PHP interpolees en dur, mais tout le
// reste du corps (ELEC/GAZ/S/estim/pMoy/calcAn/step1..3/submitLead/etc.)
// est identique octet pour octet au code inline teste (tasks #24-28).
function cmeCmpInit(UID,EDEF,CMPNONCE,CMPAJAX){

var LOGOS={
edf:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/edf_logo.png',
te:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Total-energie-logo.png',
engie:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Engie-logo-1.png',
ekwa:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/ekwateur_logo-scaled.png',
octopus:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/octopus_energy_logo.png',
ohm:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/OHM-logo.png',
ilek:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Ilek-logo.png',
plenitude:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/Logo_Plenitude.png',
butagaz:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/06/butagaz_logo.webp',
alpiq:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Alpiq-logo.png',
primeo:'https://www.comprendre-mon-energie.fr/wp-content/uploads/2026/01/Primeo-logo.png'
};

var ELEC=[
{id:'edf-bleu',logo:'edf',nom:'EDF',offre:'Tarif Bleu',type:'Tarif réglementé',px:0.19398,abo:11.80,eng:0,vert:false,tags:['Tarif officiel','Sans engagement','Garantie EDF'],c:'#1A4F8A',i:'EDF',url:'https://particulier.edf.fr/fr/accueil/electricite-gaz.html'},
{id:'primeo-elec',logo:'primeo',nom:'Primeo Énergie',offre:'Fix Confort+',type:'Offre de marché',px:0.1970,abo:8.20,eng:12,vert:false,tags:['Prix fixe 1 an','Groupe suisse'],c:'#E30613',i:'PRM',url:'https://souscription.primeo-energie.fr/mesCoordonnees'},
{id:'ohm-elec',logo:'ohm',nom:'Ohm Énergie',offre:'Prix Fixe Élec',type:'Offre locale',px:0.1980,abo:7.80,eng:12,vert:false,tags:['Prix fixe 1 an','Service client FR','Local'],c:'#FF6600',i:'OHM',url:'https://ohm-energie.com/offre/electricite'},
{id:'alpiq-elec',logo:'alpiq',nom:'Alpiq',offre:'Elec Fixe Confort',type:'Offre de marché',px:0.1995,abo:8.40,eng:12,vert:false,tags:['Groupe suisse','Prix fixe 1 an'],c:'#005A96',i:'ALP',url:'https://particuliers.alpiq.fr/electricite/notre-offre'},
{id:'ekwa-elec',logo:'ekwa',nom:'Ekwateur',offre:'Électricité Verte',type:'Offre verte',px:0.2010,abo:7.99,eng:0,vert:true,tags:['100% renouvelable','Coopérative','B-Corp'],c:'#3D8B37',i:'EKW',url:'https://ekwateur.fr/electricite-verte/'},
{id:'plen-elec',logo:'plenitude',nom:'Plenitude',offre:'Fix Électricité',type:'Offre de marché',px:0.2030,abo:8.30,eng:12,vert:false,tags:['Prix fixe 2 ans','Ex-Eni'],c:'#F5A623',i:'PLN',url:'https://www.eniplenitude.fr/offres-electricite'},
{id:'ilek-elec',logo:'ilek',nom:'ilek',offre:'Je choisis Vert',type:'Offre verte',px:0.2055,abo:8.10,eng:0,vert:true,tags:['Énergie locale','Producteurs FR'],c:'#6DBF4A',i:'ILK',url:'https://www.ilek.fr/offre-electricite'},
{id:'octopus-elec',logo:'octopus',nom:'Octopus Energy',offre:'Électricité Verte',type:'Offre verte',px:0.2075,abo:8.20,eng:0,vert:true,tags:['100% vert','App innovante'],c:'#E8107F',i:'OCT',url:'https://octopusenergy.fr/offre'},
{id:'te-fixe',logo:'te',nom:'TotalEnergies',offre:'Verte Fixe 1 an',type:'Offre de marché',px:0.2089,abo:8.90,eng:12,vert:true,tags:['Prix fixe 1 an','100% renouvelable'],c:'#E8001C',i:'TE',url:'https://www.totalenergies.fr/particuliers/electricite/offres-d-electricite'},
{id:'engie-elec',logo:'engie',nom:'Engie',offre:'Elec Moins Chère',type:'Offre de marché',px:0.2045,abo:8.50,eng:0,vert:false,tags:['Sans engagement','App mobile'],c:'#009DE0',i:'ENG',url:'https://particuliers.engie.fr/electricite.html'},
{id:'butagaz-elec',logo:'butagaz',nom:'Butagaz',offre:'Elec Sérénité',type:'Offre de marché',px:0.2095,abo:8.75,eng:0,vert:false,tags:['Groupe Shell','Sans engagement'],c:'#E85D1E',i:'BUT',url:'https://www.butagaz.fr/gaz-electricite/offres-electricite'}
];
var GAZ=[
{id:'ohm-gaz',logo:'ohm',nom:'Ohm Énergie',offre:'Gaz Prix Fixe',type:'Offre locale',px:0.0971,abo:5.70,eng:12,vert:false,tags:['Prix fixe 1 an','Service client FR'],c:'#FF6600',i:'OHM',url:'https://ohm-energie.com/offre/offre-gaz'},
{id:'engie-gaz',logo:'engie',nom:'Engie',offre:'Gaz Moins Cher',type:'Offre de marché',px:0.1045,abo:5.80,eng:0,vert:false,tags:['Sans engagement','App mobile'],c:'#009DE0',i:'ENG',url:'https://particuliers.engie.fr/gaz.html'},
{id:'plen-gaz',logo:'plenitude',nom:'Plenitude',offre:'Fix Gaz',type:'Offre de marché',px:0.1065,abo:6.00,eng:12,vert:false,tags:['Prix fixe 2 ans','Ex-Eni'],c:'#F5A623',i:'PLN',url:'https://www.eniplenitude.fr/offres-gaz'},
{id:'te-gaz',logo:'te',nom:'TotalEnergies',offre:'Gaz Fixe 1 an',type:'Offre de marché',px:0.1089,abo:5.99,eng:12,vert:false,tags:['Prix fixe 1 an'],c:'#E8001C',i:'TE',url:'https://www.totalenergies.fr/particuliers/electricite-et-gaz/offres-d-electricite-et-gaz'},
{id:'butagaz-gaz',logo:'butagaz',nom:'Butagaz',offre:'Gaz Sérénité',type:'Offre de marché',px:0.1120,abo:6.20,eng:0,vert:false,tags:['Groupe Shell','Sans engagement'],c:'#E85D1E',i:'BUT',url:'https://www.butagaz.fr/gaz-electricite/offres-electricite'},
{id:'ekwa-biogaz',logo:'ekwa',nom:'Ekwateur',offre:'Biogaz 100%',type:'Gaz vert',px:0.1180,abo:6.10,eng:0,vert:true,tags:['Biogaz 100%','B-Corp'],c:'#3D8B37',i:'EKW',url:'https://ekwateur.fr/gaz-vert-renouvelable/'},
{id:'edf-gaz',logo:'edf',nom:'EDF',offre:'Prix Repère CRE',type:'Référence CRE',px:0.12766,abo:6.49,eng:0,vert:false,tags:['Référence CRE','Prix repère'],c:'#1A4F8A',i:'EDF',url:'https://particulier.edf.fr/fr/accueil/electricite-gaz.html'}
];

// ── État global ──────────────────────────────────────────────────────────────
var S={
  step:1,
  // Demande operateur (16/11/2026) : plus de pre-remplissage automatique --
  // surface/personnes/chauffage/code postal partent vides (placeholder),
  // l'utilisateur doit les renseigner lui-meme (champs obligatoires, voir
  // step1Valide()). Seuls logement (toggle, ne peut pas etre "vide") et
  // PDL/PCE (explicitement optionnels) gardent un comportement different.
  logement:'maison',surface:'',personnes:'',chauffage:'',
  codepostal:'',pdl:'',pce:'',
  option:'base',elec:3500,gaz:8000,
  enrg:EDEF==='gaz'?'gaz':(EDEF==='dual'?'dual':'elec'),
  tab:EDEF==='gaz'?'gaz':'elec',
  edfPrix:0.19398,edfAbo:11.80,edfDate:'01/02/2026',
  gazRef:0.12766,gazAbo:6.49,gazDate:'01/02/2026'
};

// ── Calculs ──────────────────────────────────────────────────────────────────
function estim(){
  var s=parseInt(S.surface)||75,n=parseInt(S.personnes)||2;
  S.elec=Math.round(s*15+n*400+(S.chauffage==='elec'?s*28:0));
  S.gaz=S.chauffage==='gaz'?Math.round(s*60+n*500):S.chauffage==='pac'?Math.round(s*8+n*200):2000;
}
function pMoy(p,opt){
  var px=parseFloat(p)||0.19398;
  if(opt!=='hphc')return px;
  return Math.round((px*1.156*.60+px*0.726*.40)*10000)/10000;
}
function calcAn(o,kwh,opt){
  return Math.round(pMoy(o.px,opt)*(parseInt(kwh)||3500)+(parseFloat(o.abo)||9.47)*12);
}
function logClic(d){
  fetch(API+'/api/log-clic',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify(Object.assign({tool:'comparateur-energie',user_agent:navigator.userAgent.slice(0,120)},d))}).catch(function(){});
}

// ── DOM helpers ──────────────────────────────────────────────────────────────
function $(){return document.getElementById(UID);}
function mk(tag,cls,txt){
  var d=document.createElement(tag);
  if(cls)d.className=cls;
  if(txt!=null)d.textContent=txt;
  return d;
}
function ap(parent,child){parent.appendChild(child);return parent;}

// ── Icônes SVG inline (currentColor -- recoloriees par CSS via .on, aucune
// requete reseau, quelques centaines d'octets au total) pour les toggles
// (energie / logement / option tarifaire), remplace la distinction
// uniquement par couleur arbitraire (bleu/orange/violet par position)
// qui existait jusqu'ici et ne voulait rien dire semantiquement.
var TOG_ICONS={
  elec:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/></svg>',
  gaz:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2c3 4 6 7 6 11a6 6 0 1 1-12 0c0-1 .3-2 .8-3 .4 1.5 1.7 2 2.2.5-.6-2 .2-4 1.5-5.3-.2 1.6.6 2.3 1.5 1.3C11.6 5 11.8 3.3 12 2Z"/></svg>',
  dual:'<svg viewBox="0 0 24 24"><path fill="currentColor" d="M9 2 2 12h5l-1 7 7-10H8l1-7Z"/><path fill="currentColor" d="M17 9c2 2.4 4 4.4 4 7a4 4 0 1 1-8 0c0-.7.2-1.3.5-2 .3 1 1.1 1.3 1.5.3-.4-1.3.1-2.6 1-3.5-.1 1 .4 1.5 1 .8C16.7 10.7 16.8 9.8 17 9Z"/></svg>',
  maison:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5a1 1 0 0 0 1 1H9a1 1 0 0 0 1-1V16a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3.5a1 1 0 0 0 1 1h2.5a1 1 0 0 0 1-1V10"/></svg>',
  appartement:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1"/><path d="M10 21v-3a2 2 0 0 1 4 0v3"/></svg>',
  base:'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="currentColor"/></svg>',
  hphc:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path fill="currentColor" stroke="none" d="M12 3a9 9 0 0 1 0 18Z"/></svg>'
};
function mkTog(opts,val,onChange){
  var d=mk('div','tog');
  opts.forEach(function(o){
    var b=mk('button','tbtn'+(val===o.v?' on':''));
    if(o.icon&&TOG_ICONS[o.icon]){
      var ic=mk('span','ticon');ic.innerHTML=TOG_ICONS[o.icon];ap(b,ic);
    }
    ap(b,document.createTextNode(o.l));
    b.onclick=function(){
      d.querySelectorAll('.tbtn').forEach(function(x){x.className='tbtn';});
      b.className='tbtn on';
      onChange(o.v);
    };
    ap(d,b);
  });
  return d;
}

function mkInput(type,val,onChg,ph,min,max,step,ac){
  var i=document.createElement('input');
  i.type=type;i.value=val||'';
  if(ph)i.placeholder=ph;
  if(min!=null)i.min=min;
  if(max!=null)i.max=max;
  if(step)i.step=step;
  // ac (autocomplete) optionnel : 'off' coupe l'auto-remplissage du
  // navigateur (adresses/profils enregistres) sur les champs profil
  // desormais obligatoires -- demande operateur du 16/11/2026, saisie
  // volontaire plutot qu'une valeur suggeree sans verification.
  if(ac)i.autocomplete=ac;
  i.oninput=function(){onChg(i.value);};
  return i;
}
function mkField(lbl,type,val,onChg,ph,min,max,step,ac){
  var d=mk('div');
  ap(d,mk('label',null,lbl));
  ap(d,mkInput(type,val,onChg,ph,min,max,step,ac));
  return d;
}
function mkSel(lbl,opts,selIdx,onChg,placeholder){
  // placeholder (optionnel) : ajoute une option desactivee/grisee en tete
  // ("Choisissez...") selectionnee par defaut quand selIdx est null -- pas
  // de pre-selection automatique sur un vrai choix, demande operateur du
  // 16/11/2026. Reste un <select> natif (le "choix deroulant" a garder).
  var d=mk('div'),s=document.createElement('select');
  ap(d,mk('label',null,lbl));
  if(placeholder){
    var ph=document.createElement('option');
    ph.value='';ph.textContent=placeholder;ph.disabled=true;ph.hidden=true;
    if(selIdx==null||selIdx<0)ph.selected=true;
    ap(s,ph);
  }
  opts.forEach(function(o,i){
    var op=document.createElement('option');
    op.value=i;op.textContent=o;
    if(i===selIdx)op.selected=true;
    ap(s,op);
  });
  s.onchange=function(){onChg(s.value===''?null:parseInt(s.value));};
  return ap(d,s);
}
function mkLogo(o){
  var w=mk('div','logo-wrap');
  if(LOGOS[o.logo]){
    var img=new Image();
    img.alt=o.nom;
    img.width=52;img.height=52; // evite tout CLS meme avant application du CSS
    // Jusqu'a 18 cartes/logos rendus d'un coup en etape 3 -- la plupart hors
    // ecran sur mobile : lazy-load + decodage async pour ne pas faire
    // concurrence au contenu visible (CWV, demande operateur 16/11/2026).
    img.loading='lazy';img.decoding='async';
    img.onerror=function(){w.innerHTML='';var f=mk('div','logo-fb');f.style.background=o.c+'25';f.style.color=o.c;f.textContent=o.i;ap(w,f);};
    img.src=LOGOS[o.logo];
    ap(w,img);
  } else {
    var f=mk('div','logo-fb');f.style.background=o.c+'25';f.style.color=o.c;f.textContent=o.i;ap(w,f);
  }
  return w;
}

// ── StepBar ──────────────────────────────────────────────────────────────────
function mkSbar(cur){
  var labels=['Mon profil','Consommation','Offres'];
  var d=mk('div','sbar');
  labels.forEach(function(lbl,i){
    var n=i+1,done=n<cur,act=n===cur;
    var dot=mk('div','sdot'+(done?' done':act?' act':''),done?'✓':String(n));
    var sp=mk('span','slbl'+(done?' done':act?' act':''),lbl);
    var wrap=mk('div');wrap.style.cssText='display:flex;align-items:center;gap:6px;flex-shrink:0';
    ap(wrap,dot);ap(wrap,sp);ap(d,wrap);
    if(i<2)ap(d,mk('div','sline'));
  });
  return d;
}

// ── Carte offre ──────────────────────────────────────────────────────────────
function mkOfferCard(o,rang,kwh,opt,energie,refPrix){
  var best=rang===0;
  var prix=calcAn(o,kwh,opt);
  var eco=Math.max(0,refPrix-prix);
  var d=mk('div','offer-card'+(best?' best':''));

  if(best){ap(d,mk('div','best-badge','Meilleure offre'));}

  var top=mk('div','offer-top');
  ap(top,mkLogo(o));

  var info=mk('div','offer-info');
  ap(info,mk('div','offer-name',o.nom+' — '+o.offre));
  ap(info,mk('div','offer-type',o.type));
  ap(info,mk('div','offer-type',o.eng>0?'Engagement '+o.eng+' mois':'Sans engagement'));
  ap(top,info);

  var pr=mk('div','offer-price');
  ap(pr,mk('div','price-val',prix.toLocaleString('fr-FR')+'€'));
  var sub=mk('div','price-sub','/an · '+Math.round(prix/12)+'€/mois');ap(pr,sub);
  if(eco>0){ap(pr,mk('div','price-eco','−'+eco.toLocaleString('fr-FR')+'€/an'));}
  else{ap(pr,mk('div','price-ref','Référence'));}
  ap(top,pr);
  ap(d,top);

  var tags=mk('div','tags-row');
  if(o.vert){var tg=mk('span','tag tag-green','Énergie verte');ap(tags,tg);}
  o.tags.forEach(function(t){ap(tags,mk('span','tag',t));});
  ap(d,tags);

  var btn=mk('button','offer-btn'+(best?' best':''),best?'Souscrire à cette offre →':'Voir cette offre →');
  btn.onclick=function(){
    logClic({offre_id:o.id,offre_nom:o.nom+' — '+o.offre,energie:energie,kwh:kwh,prix_annuel:prix,economie:eco});
    openLeadModal({
      fournisseur:o.nom, offre:o.offre, energie:energie,
      prix_annuel:prix, economie:eco, kwh:kwh,
      option_tarifaire:S.option,
      lien_offre:o.url+'?utm_source=cme&utm_medium=comparateur&utm_campaign='+o.id
    });
  };
  ap(d,btn);
  return d;
}

// ── Étape 1 ──────────────────────────────────────────────────────────────────
function step1(root){
  var showE=S.enrg==='elec'||S.enrg==='dual';
  var showG=S.enrg==='gaz'||S.enrg==='dual';

  // Profil -- tous obligatoires sauf PDL/PCE (demande operateur du
  // 16/11/2026) : plus de valeur pre-remplie automatiquement, l'utilisateur
  // doit renseigner lui-meme chaque champ (voir step1Valide()).
  var c1=mk('div','cc');
  ap(c1,mk('div','stitle','Type de logement *'));
  ap(c1,mkTog([{v:'maison',l:'Maison',icon:'maison'},{v:'appartement',l:'Appartement',icon:'appartement'}],S.logement,function(v){S.logement=v;}));
  var g2=mk('div','g2');g2.style.marginTop='14px';
  ap(g2,mkField('Surface (m²) *','number',S.surface,function(v){S.surface=v;estim();},'ex: 75',10,500,null,'off'));
  ap(g2,mkSel('Nombre de personnes *',['1 personne','2 personnes','3 personnes','4 personnes','5+ personnes'],
    (S.personnes===''||S.personnes==null)?null:(parseInt(S.personnes)-1),
    function(v){S.personnes=(v==null)?'':v+1;estim();},'Choisissez...'));
  ap(g2,mkSel('Mode de chauffage *',['Électrique','Gaz naturel','Pompe à chaleur','Fioul / autre'],
    S.chauffage?['elec','gaz','pac','fioul'].indexOf(S.chauffage):null,
    function(v){S.chauffage=(v==null)?'':['elec','gaz','pac','fioul'][v];estim();},'Choisissez...'));
  ap(g2,mkField('Code postal *','text',S.codepostal,function(v){S.codepostal=v;},'ex: 75001',null,null,null,'off'));
  ap(c1,g2);
  ap(root,c1);

  // PDL/PCE conditionnel
  if(showE||showG){
    var cp=mk('div','cc');
    ap(cp,mk('div','stitle','Numéros de compteur (optionnel)'));
    var gp=mk('div','g2');
    if(showE){
      var dp=mk('div');
      ap(dp,mk('label',null,'N° PDL / PRM — Électricité'));
      var ip=mkInput('text',S.pdl,function(v){S.pdl=v;},'14 chiffres');
      ap(dp,ip);
      ap(dp,mk('div','hint','Sur votre facture EDF ou relevé Linky'));
      ap(gp,dp);
    }
    if(showG){
      var dc=mk('div');
      ap(dc,mk('label',null,'N° PCE — Gaz'));
      var ic=mkInput('text',S.pce,function(v){S.pce=v;},'14 chiffres');
      ap(dc,ic);
      ap(dc,mk('div','hint','Sur votre facture gaz GRDF'));
      ap(gp,dc);
    }
    ap(cp,gp);
    ap(root,cp);
  }

  // Énergie (dual uniquement)
  if(EDEF==='dual'){
    var ce=mk('div','cc');
    ap(ce,mk('div','stitle','Énergie à comparer *'));
    ap(ce,mkTog(
      [{v:'elec',l:'Électricité',icon:'elec'},{v:'gaz',l:'Gaz',icon:'gaz'},{v:'dual',l:'Électricité & Gaz',icon:'dual'}],
      S.enrg,
      function(v){S.enrg=v;S.tab=v==='gaz'?'gaz':'elec';render();}
    ));
    ap(root,ce);
  }

  var s1err=mk('div','s1err','⚠️ Merci de renseigner tous les champs obligatoires (*) ci-dessus — le code postal doit comporter 5 chiffres.');
  s1err.id=UID+'-s1err';ap(root,s1err);

  var acts=mk('div','acts');
  ap(acts,mk('div'));
  var nb=mk('button','bp','Continuer →');
  nb.onclick=function(){
    if(!step1Valide()){
      var e=document.getElementById(UID+'-s1err');
      if(e)e.style.display='block';
      return;
    }
    S.step=2;render();
  };
  ap(acts,nb);
  ap(root,acts);
}

// Champs obligatoires de l'etape 1 (tous sauf PDL/PCE, explicitement
// optionnels) -- demande operateur du 16/11/2026.
function step1Valide(){
  return !!S.logement
    && String(S.surface).trim()!==''&&parseInt(S.surface)>0
    && S.personnes!==''&&S.personnes!=null
    && !!S.chauffage
    && /^[0-9]{5}$/.test(String(S.codepostal).trim());
}

// ── Input number avec flèches natives stylisées ─────────────────────────────
function mkNumStepper(val,min,max,step,onChange){
  var inp=document.createElement('input');
  inp.type='number';
  inp.value=val;
  inp.min=min;inp.max=max;inp.step=step;
  inp.oninput=function(){var v=parseInt(inp.value);if(!isNaN(v)&&v>=min&&v<=max)onChange(v);};
  inp.onblur=function(){
    var v=parseInt(inp.value)||val;
    v=Math.max(min,Math.min(max,Math.round(v/step)*step));
    inp.value=v;onChange(v);
  };
  return inp;
}

// ── Étape 2 ──────────────────────────────────────────────────────────────────
function step2(root){
  var showE=S.enrg==='elec'||S.enrg==='dual';
  var showG=S.enrg==='gaz'||S.enrg==='dual';

  // Option tarifaire
  var ct=mk('div','cc');
  ap(ct,mk('div','stitle','Option tarifaire'));
  ap(ct,mkTog(
    [{v:'base',l:'Tarif de base',icon:'base'},{v:'hphc',l:'Heures pleines / creuses',icon:'hphc'}],
    S.option,
    function(v){S.option=v;render();}
  ));
  if(S.option==='hphc'){
    var ib=mk('div','ibox-info','Heures creuses (~22h–6h) : tarif réduit. ️ Heures pleines : tarif normal. Avantageux si vous programmez lave-linge ou chargez un VE la nuit.');
    ap(ct,ib);
  } else {
    ap(ct,mk('div','ibox-hint','Prix unique 24h/24 — idéal si votre consommation est régulière.'));
  }
  ap(root,ct);

  // Consommation
  var cc=mk('div','cc');
  ap(cc,mk('div','stitle','Consommation annuelle estimée'));
  var gc=mk('div','g2');
  if(showE){
    var de=mk('div');
    ap(de,mk('label',null,'Électricité (kWh/an)'));
    var ie=mkNumStepper(S.elec,500,30000,100,function(v){S.elec=v;updateSumm();});
    ap(de,ie);
    ap(de,mk('div','hint','Estimé selon votre profil — modifiable'));
    ap(gc,de);
  }
  if(showG){
    var dg=mk('div');
    ap(dg,mk('label',null,'Gaz (kWh/an)'));
    var ig=mkNumStepper(S.gaz,500,50000,1000,function(v){S.gaz=v;updateSumm();});
    ap(dg,ig);
    ap(dg,mk('div','hint','Estimé selon votre chauffage — modifiable'));
    ap(gc,dg);
  }
  ap(cc,gc);

  // Facture estimée interactive (élec ET gaz)
  var smWrap=mk('div');smWrap.style.cssText='display:grid;grid-template-columns:'+(showE&&showG?'1fr 1fr':'1fr')+';gap:12px;margin-top:14px';
  if(showE){
    var sm=mk('div','summ-box summ-elec');sm.style.flex='1';
    var sd=mk('div');
    var sl=mk('div');sl.style.cssText='font-size:12px;color:#9ca3af;margin-bottom:6px';sl.id=UID+'-summ-lbl';ap(sd,sl);
    var sv=mk('div');sv.style.cssText='display:flex;align-items:baseline;gap:6px;flex-wrap:wrap';
    var svv=mk('span');svv.style.cssText='font-size:20px;font-weight:700;color:#111827';svv.id=UID+'-summ-val';
    var sva=mk('span');sva.style.cssText='font-size:13px;color:#6b7280';sva.textContent='/an';
    var svm=mk('span');svm.style.cssText='font-size:12px;color:#9ca3af';svm.id=UID+'-summ-mo';
    ap(sv,svv);ap(sv,sva);ap(sv,svm);ap(sd,sv);ap(sm,sd);
    ap(sm,mk('div',null,''));ap(smWrap,sm);
  }
  if(showG){
    var smg=mk('div','summ-box summ-gaz');smg.style.flex='1';
    var sdg=mk('div');
    var slg=mk('div');slg.style.cssText='font-size:12px;color:#9ca3af;margin-bottom:6px';slg.id=UID+'-summ-gaz-lbl';ap(sdg,slg);
    var svg2=mk('div');svg2.style.cssText='display:flex;align-items:baseline;gap:6px;flex-wrap:wrap';
    var svgv=mk('span');svgv.style.cssText='font-size:20px;font-weight:700;color:#111827';svgv.id=UID+'-summ-gaz-val';
    var svga=mk('span');svga.style.cssText='font-size:13px;color:#6b7280';svga.textContent='/an';
    var svgm=mk('span');svgm.style.cssText='font-size:12px;color:#9ca3af';svgm.id=UID+'-summ-gaz-mo';
    ap(svg2,svgv);ap(svg2,svga);ap(svg2,svgm);ap(sdg,svg2);ap(smg,sdg);
    ap(smg,mk('div',null,''));ap(smWrap,smg);
  }
  ap(cc,smWrap);
  ap(root,cc);

  // Actions
  var acts=mk('div','acts');
  var bb=mk('button','bo','← Retour');
  bb.onclick=function(){S.step=1;render();};
  ap(acts,bb);
  var nb=mk('button','bp','Voir les offres →');
  nb.onclick=function(){S.step=3;render();};
  ap(acts,nb);
  ap(root,acts);

  updateSumm();
}

function updateSumm(){
  // Facture élec
  var lbl=document.getElementById(UID+'-summ-lbl');
  var val=document.getElementById(UID+'-summ-val');
  var mo=document.getElementById(UID+'-summ-mo');
  if(lbl&&val&&mo){
    var trvK=S.option==='hphc'?pMoy(S.edfPrix,'hphc'):S.edfPrix;
    var trv=Math.round(trvK*(parseInt(S.elec)||3500)+S.edfAbo*12)||0;
    lbl.textContent='Facture EDF actuelle — option '+(S.option==='hphc'?'HP/HC':'Base');
    val.textContent=trv.toLocaleString('fr-FR')+' €';
    mo.textContent='soit '+Math.round(trv/12)+' €/mois';
  }
  // Facture gaz (Prix Repère CRE)
  var glbl=document.getElementById(UID+'-summ-gaz-lbl');
  var gval=document.getElementById(UID+'-summ-gaz-val');
  var gmo=document.getElementById(UID+'-summ-gaz-mo');
  if(glbl&&gval&&gmo){
    var trvGaz=Math.round(S.gazRef*(parseInt(S.gaz)||8000)+S.gazAbo*12)||0;
    glbl.textContent='Facture gaz actuelle (Prix Repère CRE)';
    gval.textContent=trvGaz.toLocaleString('fr-FR')+' €';
    gmo.textContent='soit '+Math.round(trvGaz/12)+' €/mois';
  }
}

// ── Étape 3 ──────────────────────────────────────────────────────────────────
function step3(root){
  var offs=S.tab==='elec'?ELEC:GAZ;
  var kwh=S.tab==='elec'?(parseInt(S.elec)||3500):(parseInt(S.gaz)||8000);
  var sorted=offs.slice().sort(function(a,b){return calcAn(a,kwh,S.option)-calcAn(b,kwh,S.option);});
  var ref=sorted[sorted.length-1];
  var refPrix=calcAn(ref,kwh,S.option);
  var maxE=Math.max(0,refPrix-calcAn(sorted[0],kwh,S.option));
  var avgE=Math.max(0,Math.round(sorted.reduce(function(s,o){return s+Math.max(0,refPrix-calcAn(o,kwh,S.option));},0)/sorted.length));

  // Onglets dual
  if(EDEF==='dual'&&S.enrg==='dual'){
    var tabs=mk('div','tabs-row');
    ['elec','gaz'].forEach(function(t){
      var cnt=t==='elec'?ELEC.length:GAZ.length;
      var tb=mk('button','tab-btn'+(S.tab===t?' on':''),(t==='elec'?'Électricité':'Gaz')+' ('+cnt+')');
      tb.onclick=function(){S.tab=t;render();};
      ap(tabs,tb);
    });
    ap(root,tabs);
  }

  // En-tête résultats
  var rh=mk('div','results-head');
  var rht=mk('h3');rht.style.cssText='font-size:15px;font-weight:600;color:#111827;margin:0';
  rht.textContent=sorted.length+' offres trouvées'+(S.option==='hphc'?' · option HP/HC':'');
  ap(rh,rht);
  if(maxE>0){
    var eb=mk('span','eco-badge',"Jusqu'à "+maxE.toLocaleString('fr-FR')+'€/an');
    ap(rh,eb);
  }
  ap(root,rh);

  // Cartes offres
  sorted.forEach(function(o,i){
    ap(root,mkOfferCard(o,i,kwh,S.option,S.tab,refPrix));
  });

  // Stats résumées
  var g3=mk('div','g3');g3.style.marginTop='8px';
  [
    ['Économie moy.',avgE>0?'+'+avgE.toLocaleString('fr-FR')+'€':'—'],
    ['Offres comparées',String(sorted.length)],
    ['Meilleure offre',calcAn(sorted[0],kwh,S.option).toLocaleString('fr-FR')+'€']
  ].forEach(function(p){
    var s=mk('div','stat-card');
    ap(s,mk('div','stat-val',p[1]));
    ap(s,mk('div','stat-lbl',p[0]));
    ap(g3,s);
  });
  ap(root,g3);

  // Note légale
  ap(root,mk('div','fnote','ℹ️ Tarif EDF mis à jour depuis la CRE ('+S.edfDate+'), Prix Repère gaz CRE ('+S.gazDate+'). Offres de marché : indicatifs trimestriels. Votre facture réelle dépend de votre puissance souscrite et consommation exacte.'));

  // Boutons retour
  var acts=mk('div','acts');acts.style.marginTop='14px';
  var bm=mk('button','bo','← Modifier');
  bm.onclick=function(){S.step=2;render();};
  ap(acts,bm);
  var bn=mk('button','bo','Nouvelle recherche');
  bn.onclick=function(){S.step=1;render();};
  ap(acts,bn);
  ap(root,acts);
}

// ── Modal Lead (formulaire souscription) ──────────────────────────────────────
var LEAD_CTX=null;

function openLeadModal(ctx){
  LEAD_CTX=ctx;
  var ov=document.getElementById(UID+'-lmodal');
  if(!ov)return;
  var icon=ctx.energie==='gaz'?'\ud83d\udd25':'\u26a1';
  var summ=document.getElementById(UID+'-lm-summ');
  if(summ){
    summ.innerHTML=
      '<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">'
      +'<span style="font-size:20px">'+icon+'</span>'
      +'<div><div style="font-weight:600;font-size:15px;color:#111827">'+ctx.fournisseur+' \u2014 '+ctx.offre+'</div>'
      +'<div style="font-size:12px;color:#6b7280">'+(ctx.energie==='gaz'?'Gaz naturel':'\u00c9lectricit\u00e9')+'</div></div></div>'
      +'<div style="display:flex;gap:16px;margin-top:10px;padding-top:10px;border-top:1px solid #e5e7eb">'
      +'<div><div style="font-size:18px;font-weight:700;color:#111827">'+ctx.prix_annuel.toLocaleString('fr-FR')+'\u20ac</div><div style="font-size:11px;color:#9ca3af">par an</div></div>'
      +(ctx.economie>0?'<div><div style="font-size:18px;font-weight:700;color:#10b981">\u2212'+ctx.economie.toLocaleString('fr-FR')+'\u20ac</div><div style="font-size:11px;color:#9ca3af">\u00e9conomie/an</div></div>':'')
      +'</div>';
  }
  var err=document.getElementById(UID+'-lm-err');if(err)err.style.display='none';
  var subb=document.getElementById(UID+'-lm-sub');
  if(subb){subb.disabled=false;subb.textContent='Envoyer ma demande \u2192';}
  ov.className='lmodal-ov open';
  document.body.style.overflow='hidden';
}
function closeLeadModal(){
  var ov=document.getElementById(UID+'-lmodal');
  if(ov){ov.className='lmodal-ov';document.body.style.overflow='';}
}
function submitLead(){
  var g=function(id){return document.getElementById(UID+'-'+id);};
  // Formulaire simplifie au 16/11/2026 (demande operateur) : uniquement
  // nom&prenom (champ fusionne, meme principe que le mini-formulaire
  // inline des articles depuis le 24/10/2026) + telephone -- email/nom
  // separe retires pour reduire la friction, en particulier sur mobile.
  var prn=(g('lm-prn')||{}).value||'', tel=(g('lm-tel')||{}).value||'';
  var rgpd=g('lm-rgpd')&&g('lm-rgpd').checked;
  var err=g('lm-err');
  if(!prn.trim()||!tel.trim()||!rgpd){
    if(err)err.style.display='block';
    return;
  }
  if(err)err.style.display='none';
  var sub=g('lm-sub');
  if(sub){sub.disabled=true;sub.textContent='Envoi en cours...';}

  // Ouvrir l'onglet fournisseur IMMEDIATEMENT (geste utilisateur direct)
  // -> evite le blocage popup (window.open apres un fetch async est bloque)
  var providerTab=null;
  if(LEAD_CTX&&LEAD_CTX.lien_offre){
    providerTab=window.open('about:blank','_blank');
  }

  var data=Object.assign({
    prenom:prn.trim(),telephone:tel.trim(),
    logement:S.logement,surface:S.surface,personnes:S.personnes,chauffage:S.chauffage,
    codepostal:S.codepostal,pdl:S.pdl,pce:S.pce,
    src_post:new URLSearchParams(window.location.search).get('src_post')||''
  },LEAD_CTX);

  // Rediriger l'onglet deja ouvert vers l'offre - instantane
  if(providerTab){
    try{providerTab.location.href=LEAD_CTX.lien_offre;}catch(e){}
  }

  // Confirmation immediate, sans attendre le serveur
  showLeadSuccess();

  // Envoi en arriere-plan (email + Sheets)
  var fd=new FormData();
  fd.append('action','cme_cmp_lead');
  fd.append('nonce',CMPNONCE);
  fd.append('payload',JSON.stringify(data));
  fetch(CMPAJAX,{method:'POST',body:fd})
    .then(function(r){return r.json();})
    .then(function(res){
      console.log('[CME Lead] Reponse serveur:',res);
      if(res&&res.data)console.log('[CME Lead] Email envoye:',res.data.email_sent,'| Sheets:',res.data.gas);
    })
    .catch(function(err){console.warn('[CME Lead] Erreur:',err);});
}
function showLeadSuccess(){
  var form=document.getElementById(UID+'-lmform');
  if(form){
    var prn=(document.getElementById(UID+'-lm-prn')||{}).value||'';
    var nom='', mail=''; // champs retires du formulaire (simplification du 16/11/2026)
    var tel=(document.getElementById(UID+'-lm-tel')||{}).value||'';
    var srcPost=new URLSearchParams(window.location.search).get('src_post')||'';
    var ctx=LEAD_CTX||{};
    var leadData={
      tool:'comparateur-energie',
      source_post_id:srcPost,
      montant_estime:ctx.prix_annuel||0,
      economie_estimee:ctx.economie||0,
      details:{energie:ctx.energie||'',fournisseur:ctx.fournisseur||'',offre:ctx.offre||'',kwh:ctx.kwh||0,option_tarifaire:ctx.option_tarifaire||''}
    };
    // CHANTIER G.1 : evenement de conversion fiable, envoye au moment reel
    // du succes — independant de QUEL bouton/CTA a amene le visiteur ici
    // (article, footer, menu flottant...), et independant du statut app.
    window.dataLayer=window.dataLayer||[];
    window.dataLayer.push({
      'event':'generate_lead',
      'tool':'comparateur-energie',
      'value':ctx.economie||0,
      'source_post_id':srcPost
    });
    if(window.CME_APP_TOKEN){
      fetch('https://cme-client-api-217943559750.europe-west1.run.app/leads',{
        method:'POST',
        headers:{'Authorization':'Bearer '+window.CME_APP_TOKEN,'Content-Type':'application/json'},
        body:JSON.stringify(leadData)
      }).catch(function(){});
      form.innerHTML='<div style="text-align:center;padding:20px 10px">'
        +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
        +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
        +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Ajout\u00e9e \u00e0 vos dossiers dans l\'app.<br>Nous vous recontactons sous 48h.</div>'
        +'</div>';
    }else{
      var lienCompte='https://espace-client.comprendre-mon-energie.fr/register?prenom='
        +encodeURIComponent(prn)+'&nom='+encodeURIComponent(nom)+'&email='+encodeURIComponent(mail)+'&telephone='+encodeURIComponent(tel)
        +'&lead_data='+encodeURIComponent(JSON.stringify(leadData));
      form.innerHTML='<div style="text-align:center;padding:20px 10px">'
        +'<div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#16a34a;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 14px">\u2713</div>'
        +'<div style="font-weight:700;font-size:16px;color:#111827;margin-bottom:6px">Demande envoy\u00e9e !</div>'
        +'<div style="font-size:13px;color:#6b7280;line-height:1.5">Nous vous recontactons sous 48h.<br>L\'offre du fournisseur s\'est ouverte dans un nouvel onglet.</div>'
        +'<a href="'+lienCompte+'" target="_blank" style="display:inline-block;margin-top:16px;background:#3b82f6;color:#fff;font-weight:600;padding:12px 24px;border-radius:10px;text-decoration:none;font-size:14px">Créer mon espace client &rarr;</a>'
        +'</div>';
    }
  }
  setTimeout(closeLeadModal,6000);
}

function buildLeadModal(root){
  var ov=mk('div','lmodal-ov');ov.id=UID+'-lmodal';
  var box=mk('div','lmodal-box');

  var head=mk('div','lmodal-head');
  ap(head,mk('div',null,'\ud83d\udce9 Recevoir cette offre'));
  var sub=mk('div');sub.style.cssText='font-size:12px;color:#6b7280;font-weight:400;margin-top:2px';
  sub.textContent='Un conseiller confirme votre \u00e9ligibilit\u00e9 et vous accompagne';
  ap(head,sub);
  var cls=mk('button','lmodal-close','\u00d7');cls.type='button';cls.onclick=closeLeadModal;
  ap(head,cls);ap(box,head);

  var summ=mk('div','lmodal-summ');summ.id=UID+'-lm-summ';ap(box,summ);

  var form=mk('div');form.id=UID+'-lmform';

  // Formulaire simplifie au 16/11/2026 (demande operateur, meme principe
  // que le mini-formulaire inline des articles depuis le 24/10/2026) :
  // nom&prenom (champ fusionne) + telephone uniquement -- email et nom
  // separe retires pour reduire la friction, surtout sur mobile.
  var row1=mk('div','lmfrow');
  var fPrn=mk('input','lmfi');fPrn.id=UID+'-lm-prn';fPrn.type='text';fPrn.autocomplete='name';fPrn.placeholder='Nom et pr\u00e9nom *';
  var fTel=mk('input','lmfi');fTel.id=UID+'-lm-tel';fTel.type='tel';fTel.autocomplete='tel';fTel.placeholder='T\u00e9l\u00e9phone *';
  ap(row1,fPrn);ap(row1,fTel);ap(form,row1);

  var rgpd=mk('label','lmrgpd');
  var chk=document.createElement('input');chk.type='checkbox';chk.id=UID+'-lm-rgpd';
  var txt=mk('span');
  txt.innerHTML='J\'accepte que mes donn\u00e9es soient transmises au fournisseur pour \u00eatre recontact\u00e9, conform\u00e9ment \u00e0 notre <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" style="color:#3b82f6">politique de confidentialit\u00e9</a> et nos <a href="https://www.comprendre-mon-energie.fr/cadre-legal-et-confidentialite/" target="_blank" style="color:#3b82f6">conditions g\u00e9n\u00e9rales</a>.';
  ap(rgpd,chk);ap(rgpd,txt);ap(form,rgpd);

  var err=mk('div','lmferr','\u26a0\ufe0f Merci de remplir tous les champs et d\'accepter la politique de confidentialit\u00e9.');
  err.id=UID+'-lm-err';ap(form,err);

  var subb=mk('button','lmodal-sub','Envoyer ma demande \u2192');subb.id=UID+'-lm-sub';
  subb.type='button';subb.onclick=submitLead;ap(form,subb);

  ap(box,form);
  ov.addEventListener('click',function(e){if(e.target===ov)closeLeadModal();});
  ap(ov,box);ap(root,ov);
}

// ── Rendu principal ──────────────────────────────────────────────────────────
function render(){
  var root=$();if(!root)return;
  root.innerHTML='';

  // Header
  var hd=mk('div');hd.style.marginBottom='16px';
  ap(hd,mk('h2','page-title','Comparateur des offres Électricité & Gaz'));
  ap(hd,mk('p','page-sub',"Trouvez l'offre la moins chère selon votre profil en 2 minutes"));
  ap(root,hd);

  ap(root,mkSbar(S.step));

  if(S.step===1)step1(root);
  else if(S.step===2)step2(root);
  else step3(root);
}

// ── Init ─────────────────────────────────────────────────────────────────────
estim();
// Construire le modal UNE SEULE FOIS, hors du conteneur vide a chaque render()
(function(){
  var rootEl=$();
  if(rootEl&&rootEl.parentNode&&!document.getElementById(UID+'-lmodal')){
    buildLeadModal(rootEl.parentNode);
  }
})();
// Rendu immediat avec le prix EDF par defaut (pas d'attente reseau)
render();
// Mise a jour silencieuse du prix EDF en tache de fond (n'affecte pas le 1er rendu)
fetch(API+'/api/tarif-edf')
  .then(function(r){return r.json();})
  .then(function(d){
    if(d&&d.prix_kwh_ttc){
      S.edfPrix=d.prix_kwh_ttc;
      S.edfAbo=d.abo_mois_ttc||11.80;
      S.edfDate=d.date_debut_validite||'01/02/2026';
      ELEC.forEach(function(o){if(o.id==='edf-bleu'){o.px=S.edfPrix;o.abo=S.edfAbo;}});
      render(); // re-rendu discret si le prix a change
    }
  })
  .catch(function(){}); // silencieux : le prix par defaut reste affiche
// Mise a jour silencieuse du Prix Repere gaz CRE, meme principe que ci-dessus
fetch(API+'/api/tarif-gaz-repere')
  .then(function(r){return r.json();})
  .then(function(d){
    if(d&&d.prix_kwh_ttc){
      S.gazRef=d.prix_kwh_ttc;
      S.gazDate=d.date_debut_validite||'01/02/2026';
      GAZ.forEach(function(o){if(o.id==='edf-gaz'){o.px=S.gazRef;}}); // abo gaz : pas de source live, valeur indicative inchangee
      render();
    }
  })
  .catch(function(){});
}

// Bootstrap : initialise chaque conteneur .cme-comp present sur la page qui
// ne l est pas deja -- le marqueur data-cme-init evite une double init si ce
// fichier est charge/execute plus d une fois (defensif, WP dedup normalement
// par handle, mais filet de securite pas cher).
document.querySelectorAll('.cme-comp[data-cme-nonce]').forEach(function(el){
  if(el.getAttribute('data-cme-init'))return;
  el.setAttribute('data-cme-init','1');
  cmeCmpInit(el.id, el.getAttribute('data-eg')||'dual', el.getAttribute('data-cme-nonce'), el.getAttribute('data-ajax'));
});
})();
