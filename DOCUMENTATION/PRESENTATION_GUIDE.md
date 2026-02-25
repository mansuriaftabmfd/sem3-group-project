# SkillVerse - Presentation Notes

## Project Kya Hai

SkillVerse ek online marketplace hai jahan log apni skills sell ya khareed sakte hain.
- Client kisi bhi skill ke liye order kar sakta hai
- Provider apni service list karta hai aur orders accept karta hai
- Admin poora platform manage karta hai
- AskVera naam ka ek AI chatbot bhi hai jo users ki help karta hai

---

## Presentation Ke Time Kya Dikhana Hai

### Pehle App Run Karo
```
python run.py
Browser: http://localhost:5000
Admin: admin@skillverse.com / admin123
```

### Jinhe Demo Mein Dikhao

**1. Homepage** - categories, featured services, AskVera widget

**2. Register/Login** - client alg, provider allag register hota hai, Google login bhi hai

**3. Services Page** - filter se services dhundh sakte hain, categories hain

**4. Order Flow**
- Client kisi service pe order karta hai (wallet se payment)
- Provider accept ya reject karta hai (reject mein reason MANDATORY hai)
- Complete hone par certificate milta hai

**5. Wallet System**
- Client money add karta hai, service ke liye use karta hai
- Payment split: 90% provider ko, 10% admin ko automatically
- Transaction history dikho

**6. Admin Panel**
- Pending services approve/reject kar sakta hai
- Users dekh sakta hai, ban bhi kar sakta hai
- Admin khud orders nahi kar sakta — yeh design mein hai

**7. AskVera Chatbot**
- Corner mein floating button hai
- Role ke hisaab se alag jawab deta hai (client/provider/admin ke liye alag)
- Groq AI API use hoti hai

**8. Certificates**
- Order complete hone par provider certificate issue karta hai
- PDF generate hota hai apne aap
- Public verification page bhi hai - koi bhi verify kar sakta hai

---

## Database Tables (14 hain)

1. **users** - client, provider, admin sab yahan hain
2. **categories** - 8 categories hain (Web Dev, Design, etc.)
3. **services** - providers ki listings
4. **orders** - kaunse orders hain, status kya hai
5. **reviews** - order complete baad rating
6. **favorites** - save ki hui services
7. **notifications** - app ke andar notifications
8. **messages** - users ke beech chat
9. **availability_slots** - provider kab available hai
10. **bookings** - slot booking
11. **transactions** - wallet ka history
12. **certificates** - issued certificates
13. **testimonials** - homepage pe reviews
14. **contact_messages** - contact form se messages

---

## Possible Questions Ke Jawab

**Q: Admin kyun order nahi kar sakta?**
Admin sirf platform manage karta hai - service nahi kharidta. Usse wallet mein add money ka option hi nahi diya kyunki uski zaroorat nahi. Yeh intentional design decision hai.

**Q: Rejection reason kyun mandatory hai?**
Buyer ko pata hona chahiye kyun order reject hua. Transparency ke liye. Bina reason ke reject karna allow nahi kiya. Frontend aur backend dono check karta hai.

**Q: Payment split kaise kaam karta hai?**
Jab client ₹1000 ka order karta hai toh:
- ₹900 provider ke wallet mein jata hai
- ₹100 admin ke wallet mein platform fee ke taur par
- Yeh automatically calculate hota hai payment_system.py mein
- Transaction record hota hai database mein

**Q: Certificate kaise generate hota hai?**
ReportLab library use hoti hai PDF banane ke liye. Ek unique ID milta hai (jaise CERT-12345678). Provider order complete hone par issue karta hai. Verification page pe koi bhi ID daal ke verify kar sakta hai.

**Q: Real-time chat kaise kaam karta hai?**
Flask-SocketIO use hua hai. Jab koi message bhejta hai toh instantly dusre user ko milta hai. Page refresh ki zaroorat nahi.

**Q: AskVera kya hai?**
Yeh ek AI chatbot hai jo Groq ka API use karta hai (LLaMA model). User ka role dekh ke relevant jawab deta hai. Guest, client, provider, admin sab ke liye alag responses hain.

---

## Quick Stats

- Python files: ~20+
- HTML templates: 40+
- Database tables: 14
- Flask Blueprints: 8
- Email templates: 10
- CSS files: 4
- JS files: 2
- User roles: 3 (client, provider, admin)
- Service categories: 8

---

## Agar Kuch Kaam Na Kare

- **Database error** - PostgreSQL running hai check karo, skillverse_pg database exist karta hai check karo
- **Templates nahi mil raha** - `python run.py` root folder se chalaao, kisi aur folder se nahi
- **Port busy hai** - koi aur process 5000 pe chal rahi hai toh pehle usse band karo

Sab HTML files (ER diagram, learnproject.html) app ke bina bhi browser mein directly khul jaati hain.

---

*SkillVerse - LJ University Final Year Project*
