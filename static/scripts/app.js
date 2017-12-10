const form = {
    selectedInp: document.getElementById('selected'),
    dayIdInp: document.getElementById('day-id'),
    periodInp: document.getElementById('period'),
    groupInp: document.getElementById('group'),
    studentIdInp: document.getElementById('student-id'),
    labIdInp: document.getElementById('lab-id'),
}
const modal = document.getElementById('myModal');

function removeClassGlobally(className) {
    document.querySelectorAll(`.${className}`).forEach(el => {
        el.classList.remove(className);
    });
}

function inactivate() {
    removeClassGlobally('active')
    selectedInp.value = '';
}

function sign(el, periodNum, url) {
    modal.style.display = 'block';

    const tr = el.parentElement;
    const period = tr.parentElement.parentElement.parentElement;
    const day = period.parentElement.parentElement;
    const dayStr = day.querySelector('.day-header').querySelector('h2').innerHTML;
    const periodStr = period.querySelector('h4').innerHTML;

    form.selectedInp.value = `${dayStr} ${periodStr}`;
    form.dayIdInp.value = day.id;
    form.periodInp.value = periodNum;
    form.labIdInp.value = tr.querySelector('td').innerHTML;

    tr.classList.add('active')

    const formData = new FormData();
    for (f in form) {
        formData.append(form[f].id, form[f].value);
    }
    fetch(url, {
        method: 'POST',
        body: formData,
        credentials: "same-origin",
    }).then(d => {
        if (d.status == 200) {
            window.location = '/';
            return d.text();
        }
        else {
            return d.text();
        }
    }).then(d => {
        const content = modal.querySelector('.modal-content')
        content.innerHTML = `${d} <p>вскоре вы будете перемещены...</p>`
        setTimeout(function() {
            window.location = '/';
        }, 5000);
    })
    .catch(e => {
        console.log(e)
    });
}

function signUp(el, periodNum) {
    sign(el, periodNum, '/rest/register');
}

function signOut(el, periodNum) {
    sign(el, periodNum, '/rest/unregister');
}

function timeout(ms, promise) {
    return new Promise(function(resolve, reject) {
      setTimeout(function() {
        reject(new Error("timeout"))
      }, ms)
      promise.then(resolve, reject)
    })
  }

let hash;
fetch('/heartbeat?hash=').then(d => d.text()).then(t=>{
    hash = t;
    heartbeat();
}).catch(e => {
    window.location = '/';
})


function heartbeat() {
    Promise.race([
        fetch(`/heartbeat?hash=${hash}`),
        new Promise((resolve, reject) => {
            setTimeout(() => reject(new Error('request timeout')), 10000)
        })
    ]).then(d => d.text()).then(t => {
        window.location = '/';
    }).catch(e => {
        setTimeout(heartbeat, 1000)
    })
}

// function setPeriodActive(id, periodNum) {
//     console.log(periodNum)
//     const day = document.getElementById(id);
//     const period = day.querySelector('.periods').querySelector(`.${periodNum}`);
//     // if (!period.classList.contains('selectable')) {
//     //     return;
//     // }
//     // period.classList.add('active');
//     const dayStr = day.querySelector('.periods').querySelector('.day-header').querySelector('h2').innerHTML;
//     const periodStr = period.querySelector('h5').innerHTML;
//     selectedInp.value = `${dayStr} ${periodStr}`;
//     dayIdInp.value = id;
//     periodInp.value = periodNum;
// }

function processForm(evt) {
    if (!selectedInp.value) {
        alert('выберите время отработки!')
        return false;
    }
    if (!groupInp.value) {
        alert('введите номер группы!')
        return false;
    }
    if (!studentIdInp.value) {
        alert('введите номер студенческого!')
        return false;
    }
    return true
}
// document.onclick = inactivate;
// document.querySelectorAll('.period').onclick = setPeriodActive