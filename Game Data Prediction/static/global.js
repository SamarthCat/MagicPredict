const darkTheme = `

    :root {
        transition: 1s;
        --bgcolor: #171a21;
        --txtcolor: rgb(255, 255, 255);
        --overlaycolor: rgba(1, 1, 1, 0.3);
        --overlaycolorsolid: #101217;
        --themecolor: #F3B700;
        --themecolordark: #FF6201;
    }

    .appBody{
        backdrop-filter: grayscale(100%) brightness(50%);
    }

`;

const lightTheme = `

    :root {
        transition: 1s;
        --bgcolor: #EAEAEA;
        --txtcolor: rgb(0, 0, 0);
        --overlaycolor: rgba(0, 0, 0, 0.05);
        --overlaycolorsolid: #DEDEDE;
        --themecolor: #F3B700;
        --themecolordark: #FF6201;
    }

    .appBody{
        background-image: none !important;
    }

`;

const toast = `
<div class="toastnotify" hide="yes">
    <div style="display: flex; flex-direction: column; width: 100%; height: 100%;">
        <h1 class="toastnotifytitle" style="color: var(--bgcolor); margin: 10px; text-align: right;"></h1>
        <p class="toastnotifydesc" style="color: var(--bgcolor); margin: 10px; text-align: right; height: 100%;"></p>
    </div>
    <div class="accent" style="margin-right: 0; margin-left: auto;"></div>
</div>
`;

function sanitize(str){
    str = str.replaceAll('"', "");
    str = str.replaceAll("'", "");
    str = str.replaceAll("<", "");
    str = str.replaceAll(">", "");
    str = str.replaceAll("\\", "");
    str = str.replaceAll("/", "");
    str = str.replaceAll("|", "");
    str = str.replaceAll("{", "");
    str = str.replaceAll("}", "");
    str = str.replaceAll("`", "");
    str = str.replaceAll("^", "");
    return str;
}

function addThemeStyle(styleString) {
    const style = document.createElement('style');
    style.id = "themestyle"
    style.textContent = styleString;
    document.head.append(style);
}

function setTheme() {

    if (document.getElementById("themestyle") != undefined){
        document.getElementById("themestyle").remove();
    }

    if (localStorage.getItem("theme") == "dark"){
        addThemeStyle(darkTheme);
    }
    else if (localStorage.getItem("theme") == "light"){
        addThemeStyle(lightTheme);
    }
    else {
        var template = document.getElementById("themetext").innerHTML;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            localStorage.setItem("theme", "dark");
            template = template.replaceAll("-THEME", "light");
        }
        else{
            localStorage.setItem("theme", "light");
            template = template.replaceAll("-THEME", "dark");
        }

        template = template.replaceAll("THEME", localStorage.getItem("theme"));
        document.getElementById("themetext").innerHTML = template;
        document.getElementById("theme-notify").style.display = "initial";
        
        setTheme();
    }
    AOS.init();
}

function switchTheme(){
    if (localStorage.getItem("theme") == "dark"){
        localStorage.setItem("theme", "light");
    }
    else if (localStorage.getItem("theme") == "light"){
        localStorage.setItem("theme", "dark");
    }
    else {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            localStorage.setItem("theme", "light");
        }
        else{
            localStorage.setItem("theme", "dark");
        }
    }
    setTheme();
}

function showNotify(title, content, time){
    $(".toastnotify").attr("hide", "no");
    $(".toastnotifytitle").html(title);
    $(".toastnotifydesc").html(content);
    time = time * 1000

    window.setTimeout(() => {hideNotify()}, time)
}

function hideNotify(){
    $(".toastnotify").attr("hide", "yes");
}

function onSearchChange(val){
    if (val.value != ""){
        fetch("/autocomplete/" + val.value).then(data => {
            data.json().then(json => {
                $(".hits").empty();
                for (var i = 0; i < json["hits"].length; i++){
                    gameName = json["hits"][i]["_highlightResult"]["name"]["value"];

                    let el = document.createElement('div');
                    el.innerHTML = gameName;
                    gameName = el.innerText;
                    el.remove();

                    var searchTemplate = `
                    
                    <button onclick='redirect("/search?query=GAMENAME")' class="btninput searchbar searchhit" style="margin-top: 0; width: 100%; border: 3px solid var(--overlaycolorsolid); background-color: var(--overlaycolorsolid);">
                        <p>GAMENAME</p>
                    </button>

                    `;

                    searchTemplate = searchTemplate.replaceAll("GAMENAME", sanitize(gameName))

                    if (document.getElementById("searchinput").value != ""){
                        $(".hits").append(searchTemplate);
                    }


                }
            });
        });
    }
    else{
        $(".hits").empty();
    }
}

function redirect(loc){
    $(".trans").attr("hide", "no");
    $(".trans").attr("dir", "left");
    setTimeout(() => {
        window.location.href = loc;
    }, 300);
}

setTimeout(() => {
    $(".trans").attr("hide", "yes");
}, 300)


$("body").append(toast);
$("body").css("background-color", "");

if (window.innerWidth <= 1000){
    mobile = true;
}

try{
    var input = document.getElementById("searchinput");
    input.addEventListener("keyup", function(event) {
        if (event.key == "Enter") {
            event.preventDefault();
            document.getElementsByClassName("searchbutton")[0].click();
        }
    });
}
catch{
    
}



if (localStorage.getItem("first") != "false"){
    showNotify("Welcome!", `By using this website, you agree to the <a href="https://samsidparty.com/privacypolicy.html" style="color: #7A42FF;">SamsidParty Terms Of Service</a>.`, 5);
    $(".firstboot").removeClass("firstboot");
    localStorage.setItem("first", "false");
}

setTheme();

