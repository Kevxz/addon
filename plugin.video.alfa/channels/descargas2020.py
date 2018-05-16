# -*- coding: utf-8 -*-

import re
import sys
import urllib
import urlparse

from channelselector import get_thumb
from core import httptools
from core import scrapertools
from core import servertools
from core.item import Item
from platformcode import config, logger
from core import tmdb

host = 'http://descargas2020.com/'

def mainlist(item):
    logger.info()

    itemlist = []

    thumb_pelis = get_thumb("channels_movie.png")
    thumb_pelis_hd = get_thumb("channels_movie_hd.png")
    thumb_series = get_thumb("channels_tvshow.png")
    thumb_series_hd = get_thumb("channels_tvshow_hd.png")
    thumb_series_az = get_thumb("channels_tvshow_az.png")
    thumb_docus = get_thumb("channels_documentary.png")
    thumb_buscar = get_thumb("search.png")

    itemlist.append(Item(channel=item.channel, action="submenu", title="Películas", url=host,
                         extra="peliculas", thumbnail=thumb_pelis ))

    itemlist.append(Item(channel=item.channel, action="submenu", title="Series", url=host, extra="series",
                         thumbnail=thumb_series))
                         
    itemlist.append(Item(channel=item.channel, action="submenu", title="Documentales", url=host, extra="varios",
                         thumbnail=thumb_docus))
    itemlist.append(
        Item(channel=item.channel, action="search", title="Buscar", url=host + "buscar", thumbnail=thumb_buscar))

    return itemlist

def submenu(item):
    logger.info()
    itemlist = []

    data = re.sub(r"\n|\r|\t|\s{2}|(<!--.*?-->)", "", httptools.downloadpage(item.url).data)
    data = unicode(data, "iso-8859-1", errors="replace").encode("utf-8")
    data = data.replace("'", '"').replace('/series"', '/series/"')   #Compatibilidad con mispelisy.series.com

    host_dom = host.replace("https://", "").replace("http://", "").replace("www.", "")
    patron = '<li><a href="http://(?:www.)?' + host_dom + item.extra + '/">.*?<ul.*?>(.*?)</ul>'
    if "pelisyseries.com" in host and item.extra == "varios":      #compatibilidad con mispelisy.series.com
        data = '<a href="' + host + 'varios/" title="Documentales"><i class="icon-rocket"></i> Documentales</a>'
    else:
        if data:
            data = scrapertools.get_match(data, patron)
        else:
            return itemlist

    patron = '<.*?href="([^"]+)".*?>([^>]+)</a>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in matches:
        title = scrapedtitle.strip()
        url = scrapedurl

        itemlist.append(Item(channel=item.channel, action="listado", title=title, url=url, extra=item.extra))
        itemlist.append(
            Item(channel=item.channel, action="alfabeto", title=title + " [A-Z]", url=url, extra=item.extra))
            
    if item.extra == "peliculas":
        itemlist.append(Item(channel=item.channel, action="listado", title="Películas 4K", url=host + "peliculas-hd/4kultrahd/", extra=item.extra))
        itemlist.append(
            Item(channel=item.channel, action="alfabeto", title="Películas 4K" + " [A-Z]", url=host + "peliculas-hd/4kultrahd/", extra=item.extra))
            
    return itemlist


def alfabeto(item):
    logger.info()
    itemlist = []

    data = re.sub(r"\n|\r|\t|\s{2}|(<!--.*?-->)", "", httptools.downloadpage(item.url).data)
    data = unicode(data, "iso-8859-1", errors="replace").encode("utf-8")

    patron = '<ul class="alfabeto">(.*?)</ul>'
    if data:
        data = scrapertools.get_match(data, patron)
    else:
        return itemlist

    patron = '<a href="([^"]+)"[^>]+>([^>]+)</a>'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle in matches:
        title = scrapedtitle.upper()
        url = scrapedurl

        itemlist.append(Item(channel=item.channel, action="listado", title=title, url=url, extra=item.extra))

    return itemlist


def listado(item):
    logger.info()
    itemlist = []
    clase = "pelilist"      # etiqueta para localizar zona de listado de contenidos
    url_next_page =''       # Controlde paginación
    cnt_tot = 30            # Poner el num. máximo de items por página

    if item.category:
        del item.category
    if item.totalItems:
        del item.totalItems

    data = re.sub(r"\n|\r|\t|\s{2}|(<!--.*?-->)", "", httptools.downloadpage(item.url).data)

    #Establecemos los valores básicos en función del tipo de contenido
    if item.extra == "peliculas":
        item.action = "findvideos"
        item.contentType = "movie"
        pag = True                                          #Sí hay paginación
    elif item.extra == "series" and not "/miniseries" in item.url:
        item.action = "episodios"
        item.contentType = "tvshow"
        pag = True
    elif item.extra == "varios" or "/miniseries" in item.url:
        item.action = "findvideos"
        item.contentType = "movie"
        pag = True
    
    #Selecciona el tramo de la página con el listado de contenidos
    patron = '<ul class="' + clase + '">(.*?)</ul>'
    if data:
        fichas = scrapertools.get_match(data, patron)
    else:
        return itemlist
    page_extra = clase

    #Scrapea los datos de cada vídeo.  Título alternativo se mantiene, aunque no se usa de momento
    patron = '<a href="([^"]+).*?'  # la url
    patron += 'title="([^"]+).*?'  # el titulo
    patron += '<img.*?src="([^"]+)"[^>]+>.*?'  # el thumbnail
    patron += '<h2.*?>(.*?)?<\/h2>'  # titulo alternativo.  Se trunca en títulos largos
    patron += '<span>([^<].*?)?<'  # la calidad
    matches = re.compile(patron, re.DOTALL).findall(fichas)
    #logger.debug("MATCHES: " + str(len(matches)))
    #logger.debug(matches)
    #logger.debug("patron: " + patron + " / fichas: " + fichas)

    # Identifico la página actual y el total de páginas para el pie de página
    total_pag  = scrapertools.find_single_match(data,'<a href=".*?(\d+)?">Last<\/a><\/li>')

    if not item.post_num:
        post_num = 1
    else:
        post_num = int(item.post_num) + 1
    if not total_pag:
        total_pag = 1
    #Calcula las páginas del canal por cada página de la web
    total_pag = int(total_pag) * int((float(len(matches))/float(cnt_tot)) + 0.999999)
    
    # Preparamos la paginación.
    if not item.cnt_pag:
        cnt_pag = 0
    else:
        cnt_pag = item.cnt_pag
        del item.cnt_pag
    
    matches_cnt = len(matches)
    if item.next_page != 'b':
        if matches_cnt > cnt_pag + cnt_tot:
            url_next_page = item.url
        matches = matches[cnt_pag:cnt_pag+cnt_tot]
        next_page = ''
        if matches_cnt <= cnt_pag + (cnt_tot * 2):
            if pag:
                next_page = 'b'
        modo = 'continue'
    else:
        matches = matches[cnt_pag:cnt_pag+cnt_tot]
        next_page = 'a'
        patron_next_page  = '<a href="([^"]+)">Next<\/a>'
        matches_next_page = re.compile(patron_next_page, re.DOTALL).findall(data)
        modo = 'continue'
        if len(matches_next_page) > 0:
            url_next_page = urlparse.urljoin(item.url, matches_next_page[0])
            modo = 'next'
    
    # Avanzamos el contador de líneas en una página
    if item.next_page:
        del item.next_page
    if modo == 'next':
        cnt_pag = 0
    else:
        cnt_pag += cnt_tot

    #Tratamos todos los contenidos, creardo una variable local de Item
    for scrapedurl, scrapedtitle, scrapedthumbnail, title_alt, calidad in matches:
        item_local = item.clone()
        if item_local.tipo:
            del item_local.tipo
        if item_local.totalItems:
            del item_local.totalItems
        if item.post_num:
            del item.post_num

        item_local.title = ''
        item_local.context = "['buscar_trailer']"
        
        # Limpiamos títulos, Sacamos datos de calidad, audio y lenguaje
        title = re.sub('\r\n', '', scrapedtitle).decode('iso-8859-1').encode('utf8').strip()
        title_alt = re.sub('\r\n', '', title_alt).decode('iso-8859-1').encode('utf8').strip()
        title = title.replace("á", "a", 1).replace("é", "e", 1).replace("í", "i", 1).replace("ó", "o", 1).replace("ú", "u", 1).replace("ü", "u", 1).replace("ï¿½", "ñ").replace("Ã±", "ñ")
        title_alt = title_alt.replace("á", "a", 1).replace("é", "e", 1).replace("í", "i", 1).replace("ó", "o", 1).replace("ú", "u", 1).replace("ü", "u", 1).replace("ï¿½", "ñ").replace("Ã±", "ñ")
        
        item_local.quality = calidad
        title_subs = []
        
        #Determinamos y marcamos idiomas distintos del castellano
        item_local.language = ""
        if "[vos" in title.lower()  or "v.o.s" in title.lower() or "vo" in title.lower() or ".com/pelicula/" in scrapedurl  or ".com/series-vo" in scrapedurl or "-vo/" in scrapedurl or "vos" in calidad.lower() or "vose" in calidad.lower() or "v.o.s" in calidad.lower() or ".com/peliculas-vo" in item.url:
            item_local.language = "VOS"
        title = title.replace(" [Subs. integrados]", "").replace(" [subs. Integrados]", "").replace(" [VOSE", "").replace(" [VOS", "").replace(" (V.O.S.E)", "").replace(" VO", "")
        if "latino" in title.lower() or "argentina" in title.lower() or "-latino/" in scrapedurl or "latino" in calidad.lower() or "argentina" in calidad.lower():
            item_local.language = "LAT"
        
        #Guardamos info de 3D en calidad y limpiamos
        if "3d" in title.lower():
            if not "3d" in item_local.quality.lower():
                item_local.quality = item_local.quality + " 3D"
            calidad3D = scrapertools.find_single_match(title, r'\s(3[d|D]\s\w+)')
            if calidad3D:
                item_local.quality = item_local.quality.replace("3D", calidad3D)
            title = re.sub(r'\s3[d|D]\s\w+', '', title)
            title = re.sub(r'\s3[d|D]', '', title)
            title_alt = re.sub(r'\s3[d|D]\s\w+', '', title_alt)
            title_alt = re.sub(r'\s3[d|D]', '', title_alt)
            if "imax" in title.lower():
                item_local.quality = item_local.quality + " IMAX"
                title = title.replace(" IMAX", "").replace(" imax", "")
                title_alt = title_alt.replace(" IMAX", "").replace(" imax", "")
        if "2d" in title.lower():
            title = title.replace("(2D)", "").replace("(2d)", "").replace("2D", "").replace("2d", "")
            title_subs += ["[2D]"]
        
        #Extraemos info adicional del título y la guardamos para después de TMDB
        if "temp" in title.lower() or "cap" in title.lower():        #Eliminamos Temporada, solo nos interesa la serie completa
            title = re.sub(r' - [t|T]emp\w+ \d+x\d+', '', title)
            title = re.sub(r' - [t|T]emp\w+ \d+', '', title)
            title = re.sub(r' - [t|T]emp\w+.*?\d+', '', title)
            title = re.sub(r' [t|T]emp.*?\d+x\d+', '', title)
            title = re.sub(r' [t|T]emp.*?\d+', '', title)
            title = re.sub(r' [c|C]ap.*?\d+', '', title)
        if "audio" in title.lower():        #Reservamos info de audio para después de TMDB
            title_subs += ['[%s]' % scrapertools.find_single_match(title, r'(\[[a|A]udio.*?\])')]
            title = re.sub(r'\[[a|A]udio.*?\]', '', title)
        if "[dual" in title.lower() or "multileng" in title.lower() or "multileng" in item_local.quality.lower():
            item_local.language = "DUAL"
            title = re.sub(r'\[[D|d]ual.*?\]', '', title)
            title = re.sub(r'\[[M|m]ultileng.*?\]', '', title)
            item_local.quality = re.sub(r'\[[M|m]ultileng.*?\]', '', item_local.quality)
        if "duolog" in title.lower():
            title_subs += ["[Saga]"]
            title = title.replace(" Duologia", "").replace(" duologia", "").replace(" Duolog", "").replace(" duolog", "")
        if "trilog" in title.lower():
            title_subs += ["[Saga]"]
            title = title.replace(" Trilogia", "").replace(" trilogia", "").replace(" Trilog", "").replace(" trilog", "")
        if "extendida" in title.lower():
            title_subs += ["[V. Extendida]"]
            title = title.replace(" Version Extendida", "").replace(" (Version Extendida)", "").replace(" V. Extendida", "").replace(" VExtendida", "").replace(" V Extendida", "")
        if "saga" in title.lower():
            title = title.replace(" Saga Completa", "").replace(" saga sompleta", "").replace(" Saga", "").replace(" saga", "")
            title_subs += ["[Saga]"]
        if "colecc" in title.lower() or "completa" in title.lower():
            title = title.replace(" Coleccion", "").replace(" coleccion", "").replace(" Colecci", "").replace(" colecci", "").replace(" Completa", "").replace(" completa", "").replace(" COMPLETA", "")
        if scrapertools.find_single_match(title, r'(- [m|M].*?serie ?\w+)'):
            title = re.sub(r'- [m|M].*?serie ?\w+', '', title)
            title_subs += ["[Miniserie]"]

        #Limpiamos restos en título
        title = title.replace("Castellano", "").replace("castellano", "").replace("inglés", "").replace("ingles", "").replace("Inglés", "").replace("Ingles", "").replace("Espa", "").replace("Ingl", "").replace("Engl", "").replace("Calidad", "").replace("de la Serie", "")
        title_alt = title_alt.replace("Castellano", "").replace("castellano", "").replace("inglés", "").replace("ingles", "").replace("Inglés", "").replace("Ingles", "").replace("Espa", "").replace("Ingl", "").replace("Engl", "").replace("Calidad", "").replace("de la Serie", "")
        
        #Limpiamos cabeceras y colas del título
        if not "torrentrapid.com" in host:
            title = re.sub(r'Descargar\s', '', title)
        else:
            title = re.sub(r'Descargar\s\w+\s', '', title)
        title = re.sub(r'Descargar\s\w+\-\w+', '', title)
        title = re.sub(r'\(COMPLE.*?\)', '', title)
        title = re.sub(r'\(\d{4}\)$', '', title)
        title = re.sub(r'\d{4}$', '', title)
        title = re.sub(r' \d+x\d+', '', title)
        title = re.sub(r' x\d+', '', title)
        title = title.replace("Ver online ", "").replace("Descarga Serie HD ", "").replace("Descargar Serie HD ", "").replace("Descarga Serie ", "").replace("Ver en linea ", "").replace("Ver en linea", "").replace("HD ", "").replace("(Proper)", "").replace("DVD", "").replace("- ES ", "").replace("ES ", "").replace("COMPLETA", "").strip()
        title = title.replace("Descargar torrent ", "").replace("Descarga Gratis ", "").replace("Descargar Estreno ", "").replace("Pelicula en latino ", "").replace("Descargar Pelicula ", "").replace("Descargar Peliculas ", "").replace("Descargar Todas ", "").replace("Descargar ", "").replace("Descarga ", "").replace("Bajar ", "").replace("RIP ", "").replace("1080p ", "").replace("720p ", "").replace("DVD-Screener ", "").replace("Bonus Disc", "").replace("de Cine ", "").replace("latino", "").replace("Latino", "").replace("argentina", "").replace("Argentina", "").strip()
        if title.endswith("torrent gratis"): title = title[:-15]
        if title.endswith("gratis"): title = title[:-7]
        if title.endswith("torrent"): title = title[:-8]
        if title.endswith("en HD"): title = title[:-6]
        if title.endswith(" -"): title = title[:-2]
        if "en espa" in title: title = title[:-11]
        
        item_local.quality = item_local.quality.replace("gratis ", "")
        if "HDR" in title:
            title = title.replace(" HDR", "")
            if not "HDR" in item_local.quality:
                item_local.quality += " HDR"
        
        while title.endswith(' '):
            title = title[:-1]
        while title_alt.endswith(' '):
            title_alt = title_alt[:-1]
        while item_local.quality.endswith(' '):
            item_local.quality = item_local.quality[:-1]

        if not title:       #Usamos solo el title_alt en caso de que no exista el título original
            title = title_alt
            if not title:
                title = "SIN TITULO"
        
        #Limpieza final del título y guardado en las variables según su tipo de contenido
        title = scrapertools.remove_htmltags(title)
        item_local.title = title
        if item_local.contentType == "movie":
            item_local.contentTitle = title
        else:
            item_local.contentSerieName = title
        
        #Guardamos el resto de variables del vídeo
        item_local.url = scrapedurl
        item_local.thumbnail = scrapedthumbnail
        item_local.contentThumbnail = scrapedthumbnail

        #Guardamos el año que puede venir en la url, por si luego no hay resultados desde TMDB
        year = ''
        if item_local.contentType == "movie": 
            year = scrapertools.find_single_match(scrapedurl, r'(\d{4})')
        if year >= "1900" and year <= "2040" and year != "2020":
            title_subs += [year]
        item_local.infoLabels['year'] = '-'
        
        #Guarda la variable temporal que almacena la info adicional del título a ser restaurada después de TMDB
        item_local.title_subs = title_subs
        
        #Agrega el item local a la lista itemlist
        itemlist.append(item_local.clone())

    #Pasamos a TMDB la lista completa Itemlist
    tmdb.set_infoLabels(itemlist, True)
    
    # Pasada para maquillaje de los títulos obtenidos desde TMDB
    for item_local in itemlist:
        title = item_local.title

        #Restauramos la info adicional guarda en la lista title_subs, y la borramos de Item
        if len(item_local.title_subs) > 0:
            title += " "
        for title_subs in item_local.title_subs:
            if "audio" in title_subs.lower():
                title = '%s [%s]' % (title, scrapertools.find_single_match(title_subs, r'[a|A]udio (.*?)'))
                continue
            if scrapertools.find_single_match(title_subs, r'(\d{4})'):
                if not item_local.infoLabels['year'] or item_local.infoLabels['year'] == "-":
                    item_local.infoLabels['year'] = scrapertools.find_single_match(title_subs, r'(\d{4})')
                continue
            if not config.get_setting("unify"):         #Si Titulos Inteligentes NO seleccionados:
                title = '%s %s' % (title, title_subs)
            else:
                title = '%s -%s-' % (title, title_subs)
        del item_local.title_subs
        
        # Si TMDB no ha encontrado el vídeo limpiamos el año
        if item_local.infoLabels['year'] == "-":
            item_local.infoLabels['year'] = ''
            item_local.infoLabels['aired'] = ''
            
        # Preparamos el título para series, con los núm. de temporadas, si las hay
        if item_local.contentType == "season" or item_local.contentType == "tvshow":
            item_local.contentTitle= ''

        rating = ''
        if item_local.infoLabels['rating'] and item_local.infoLabels['rating'] != '0.0':
            rating = float(item_local.infoLabels['rating'])
            rating = round(rating, 1)
        
        #Ahora maquillamos un poco los titulos dependiendo de si se han seleccionado títulos inteleigentes o no
        if not config.get_setting("unify"):         #Si Titulos Inteligentes NO seleccionados:
            if item_local.contentType == "season" or item_local.contentType == "tvshow":
                    title = '%s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (title, scrapertools.find_single_match(str(item_local.infoLabels['aired']), r'\/(\d{4})'), rating, item_local.quality, item_local.language)
            
            elif item_local.contentType == "movie":
                title = '%s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (title, str(item_local.infoLabels['year']), rating, item_local.quality, item_local.language)

        if config.get_setting("unify"):         #Si Titulos Inteligentes SÍ seleccionados:
            title = title.replace("[", "-").replace("]", "-")
        
        title = title.replace("--", "").replace(" []", "").replace("()", "").replace("(/)", "").replace("[/]", "")
        title = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', title)
        title = re.sub(r'\s\[COLOR \w+\]\[\/COLOR\]', '', title)
        item_local.title = title
        
        #logger.debug("url: " + item_local.url + " / title: " + item_local.title + " / content title: " + item_local.contentTitle + "/" + item_local.contentSerieName + " / calidad: " + item_local.quality + " / year: " + year)
        #logger.debug(item_local)

    if len(itemlist) == 0:
        itemlist.append(Item(channel=item.channel, action="mainlist", title="No se ha podido cargar el listado"))
    else:
        if url_next_page:
            itemlist.append(
                Item(channel=item.channel, action="listado", title="[COLOR gold][B]Pagina siguiente >> [/B][/COLOR]" + str(post_num) + " de " + str(total_pag), url=url_next_page, next_page=next_page, cnt_pag=cnt_pag, post_num=post_num, pag=pag, modo=modo, extra=item.extra))
                
    #logger.debug(url_next_page + " / " + next_page + " / " + str(matches_cnt) + " / " + str(cnt_pag)+ " / " + str(total_pag)  + " / " + str(pag)  + " / " + modo + " / " + item.extra)
    
    return itemlist

def listado_busqueda(item):
    logger.info()
    itemlist = []
    cnt_tot = 40            # Poner el num. máximo de items por página.  Dejamos que la web lo controle
    cnt_title = 0           # Contador de líneas insertadas en Itemlist
    cnt_pag = 0             # Contador de líneas leídas de Matches
    
    if item.cnt_pag:
        cnt_pag = item.cnt_pag      # Se guarda en la lista de páginas anteriores en Item
        del item.cnt_pag

    if item.category:
        del item.category
    if item.totalItems:
        del item.totalItems
    if item.text_bold:
        del item.text_bold
    if item.text_color:
        del item.text_color

    #Sistema de paginado para evitar páginas vacías o semi-vacías en casos de búsquedas con series con muchos episodios
    title_lista = []        # Guarda la lista de series que ya están en Itemlist, para no duplicar lineas
    if item.title_lista:    # Si viene de una pasada anterior, la lista ya estará guardada
        title_lista = item.title_lista      # Se usa la lista de páginas anteriores en Item
    title_lista_alt = []
    for url in title_lista:
        title_lista_alt += [url]        #hacemos una copia no vinculada de title_lista
    matches = []
    cnt_next = 0
    total_pag = 1
    post_num = 1
    
    #Máximo num. de líneas permitidas por TMDB. Máx de 5 páginas por Itemlist para no degradar el rendimiento
    while cnt_title <= cnt_tot and cnt_next < 5:

        data = re.sub(r"\n|\r|\t|\s{2,}", "", httptools.downloadpage(item.url, post=item.post).data)
        cnt_next += 1
        if not data:        #Si la web está caída salimos sin dar error
            return itemlist

        #Obtiene la dirección de la próxima página, si la hay
        try:
            post_actual = item.post     #Guardamos el post actual por si hay overflow de Itemlist y hay que hechar marcha atrás
            get, post, total_pag = scrapertools.find_single_match(data, '<ul class="pagination">.*?<a\s*href="([^"]+)"(?:\s*onClick=".*?\(\'([^"]+)\'\);">Next<\/a>.*?onClick=".*?\(\'([^"]+)\'\);">Last<\/a>)')
        except:
            post = False
            cnt_next = 99       #No hay más páginas.  Salir del bucle después de procesar ésta

        if post:        #puntero a la siguiente página.  Cada página de la web tiene 30 entradas
            if "pg" in item.post:
                item.post = re.sub(r"pg=(\d+)", "pg=%s" % post, item.post)
            else:
                item.post += "&pg=%s" % post
            post_num = int(post)-1      #Guardo página actual

        # Preparamos un patron que pretence recoger todos los datos significativos del video
        pattern = '<ul class="%s">(.*?)</ul>' % item.pattern        #seleccionamos en bloque que nos interesa    
        data = scrapertools.get_match(data, pattern)
        #pattern = '<li[^>]*><a href="(?P<url>[^"]+).*?<img.*?src="(?P<thumb>[^"]+)?".*?<h2.*?>(?P<title>.*?)?<\/h2>'
        pattern = '<li[^>]*><a href="(?P<scrapedurl>[^"]+).*?'      #url
        pattern += 'title="(?P<scrapedtitle>[^"]+).*?'              #título
        pattern += '<img.*?src="(?P<scrapedthumbnail>[^"]+)?".*?'   #thumb
        pattern += '<h2.*?(?P<calidad>\[.*?)?<\/h2.*?'              #calidad
        pattern += '<span.*?>\d+-\d+-(?P<year>\d{4})?<\/span>*.?'   #año
        pattern += '<span.*?>(?P<size>\d+[\.|\s].*?[GB|MB])?<\/span>'  #tamaño (significativo para peliculas)
        matches_alt = re.compile(pattern, re.DOTALL).findall(data)
        
        #Ahora se hace una simulación para saber cuantas líneas podemos albergar en este Itemlist.
        #Se controlará cuantas páginas web se tienen que leer para rellenar la lista, sin pasarse
        for scrapedurl, scrapedtitle, scrapedthumbnail, calidad, year, size in matches_alt:
            
            #Realiza un control de las series que se añaden, ya que el buscador devuelve episodios y no las series completas
            #Se analiza si la url de la serie ya se ha listado antes.  Si es así, esa entrada se ignora
            #Cuando llega al num. máximo de entradas por página, la pinta y guarda los contadores y la lista de series
            if "pelisyseries.com" in host:          #Excepción para mispelisyseries.com.
                scrapedurl_alt = scrapedurl
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-\d+-al-\d+', '', scrapedurl_alt) #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-\d+', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/\d{5,7}', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                if scrapedurl_alt in title_lista_alt:       # si ya se ha tratado, pasamos al siguiente item
                    continue                                # solo guardamos la url para series y docus

            if scrapedurl in title_lista_alt:       # si ya se ha tratado, pasamos al siguiente item
                continue                            # solo guardamos la url para series y docus

            if ".com/serie" in scrapedurl or "/serie" in scrapedurl or "-serie" in scrapedurl or "varios/" in scrapedurl:
                if "pelisyseries.com" in host:
                    title_lista_alt += [scrapedurl_alt]
                else:
                    title_lista_alt += [scrapedurl]
            if "juego/" in scrapedurl:      # no mostramos lo que no sean videos
                continue
            cnt_title += 1                  # Sería una línea real más para Itemlist
            
            #Control de página
            if cnt_title > cnt_tot*0.65:        #si se acerca al máximo num. de lineas por pagina, tratamos lo que tenemos
                cnt_next = 99                   #Casi completo, no sobrepasar con la siguiente página
                if cnt_title > cnt_tot:
                    cnt_title = 99              #Sobrepasado el máximo.  Ignoro página actual
                    item.post = post_actual     #Restauro puntero "next" a la página actual, para releearla en otra pasada
                    post_num -= 1               #Restauro puntero a la página actual en el pie de página
                    break

        if cnt_title <= cnt_tot:
            matches.extend(matches_alt)         #Acumulamos las entradas a tratar. Si nos hemos pasado ignoro última página
    
    #logger.debug("PATRON: " + pattern)
    #logger.debug(matches)
    #logger.debug(data)

    cnt_title = 0
    for scrapedurl, scrapedtitle, scrapedthumbnail, calidad, year, size in matches:
        cnt_pag += 1 
        
        #Realiza un control de las series que se añaden, ya que el buscador devuelve episodios y no las series completas
        #Se analiza si la url de la serie ya se ha listado antes.  Si es así, esa entrada se ignora
        #El control de página ya se ha realizado más arriba
        if "pelisyseries.com" in host:          #Excepción para mispelisyseries.com.
                scrapedurl_alt = scrapedurl
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-\d+-al-\d+', '', scrapedurl_alt) #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-\d+', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/[c|C]ap.*?-', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                scrapedurl_alt = re.sub(r'\/\d{5,7}', '', scrapedurl_alt)    #Scrapeo el capítulo para hacerlo serie
                if scrapedurl_alt in title_lista:       # si ya se ha tratado, pasamos al siguiente item
                    continue                                # solo guardamos la url para series y docus

        if scrapedurl in title_lista:       # si ya se ha tratado, pasamos al siguiente item
            continue                            # solo guardamos la url para series y docus

        if ".com/serie" in scrapedurl or "/serie" in scrapedurl or "-serie" in scrapedurl or "varios/" in scrapedurl:
            if "pelisyseries.com" in host:
                title_lista += [scrapedurl_alt]
            else:
                title_lista += [scrapedurl]
        if "juego/" in scrapedurl:      # no mostramos lo que no sean videos
            continue
        cnt_title += 1                  # Sería una línea real más para Itemlist
        
        #Creamos una copia de Item para cada contenido
        item_local = item.clone()
        if item_local.tipo:
            del item_local.tipo
        if item_local.totalItems:
            del item_local.totalItems
        if item_local.post:
            del item_local.post
        if item_local.pattern:
            del item_local.pattern
        if item_local.title_lista:
            del item_local.title_lista
        item_local.title = ''
        item_local.context = "['buscar_trailer']"
        
        #Establecemos los valores básicos en función del tipo de contenido
        if (".com/serie" in scrapedurl or "/serie" in scrapedurl or "-serie" in scrapedurl) and not "/miniseries" in scrapedurl:      #Series
            item_local.action = "episodios"
            item_local.contentType = "tvshow"
            item_local.extra = "series"
        elif "varios/" in scrapedurl or "/miniseries" in scrapedurl:               #Documentales y varios
            item_local.action = "findvideos"
            item_local.contentType = "movie"
            item_local.extra = "varios"
        else:                                       #Películas
            item_local.action = "findvideos"
            item_local.contentType = "movie"
            item_local.extra = "peliculas"
        
        # Limpiamos títulos, Sacamos datos de calidad, audio y lenguaje
        title = re.sub('\r\n', '', scrapedtitle).decode('iso-8859-1').encode('utf8').strip()
        title = title.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ü", "u").replace("ï¿½", "ñ").replace("Ã±", "ñ")
        
        item_local.quality = scrapertools.htmlclean(calidad)
        title_subs = []
        
        #Determinamos y marcamos idiomas distintos del castellano
        item_local.language = ""
        if "[vos" in title.lower()  or "v.o.s" in title.lower() or "vo" in title.lower() or ".com/pelicula/" in scrapedurl  or ".com/series-vo" in scrapedurl or "-vo/" in scrapedurl or "vos" in calidad.lower() or "vose" in calidad.lower() or "v.o.s" in calidad.lower():
            item_local.language = "VOS"
        title = title.replace(" [Subs. integrados]", "").replace(" [subs. Integrados]", "").replace(" [VOSE", "").replace(" [VOS", "").replace(" (V.O.S.E)", "").replace(" VO", "")
        if "latino" in title.lower() or "argentina" in title.lower() or "-latino/" in scrapedurl or "latino" in calidad.lower() or "argentina" in calidad.lower():
            item_local.language = "LAT"
        
        #Guardamos info de 3D en calidad y limpiamos
        if "3d" in title.lower():
            if not "3d" in item_local.quality.lower():
                item_local.quality = "3D " + item_local.quality
            calidad3D = scrapertools.find_single_match(title, r'\s(3[d|D]\s\w+)')
            if calidad3D:
                item_local.quality = item_local.quality.replace("3D", calidad3D)
            title = re.sub(r'\s3[d|D]\s\w+', '', title)
            title = re.sub(r'\s3[d|D]', '', title)
            if "imax" in title.lower():
                item_local.quality = item_local.quality + " IMAX"
                title = title.replace(" IMAX", "").replace(" imax", "")
        if "2d" in title.lower():
            title = title.replace("(2D)", "").replace("(2d)", "").replace("2D", "").replace("2d", "")
            title_subs += ["[2D]"]
        
        #Extraemos info adicional del título y la guardamos para después de TMDB
        if ("temp" in title.lower() or "cap" in title.lower()) and item_local.contentType != "movie":
            #Eliminamos Temporada de Series, solo nos interesa la serie completa
            title = re.sub(r' - [t|T]emp\w+ \d+[x|X]\d+', '', title)
            title = re.sub(r' - [t|T]emp\w+ \d+', '', title)
            title = re.sub(r' - [t|T]emp\w+.*?\d+', '', title)
            title = re.sub(r' [t|T]emp.*?\d+[x|X]\d+', '', title)
            title = re.sub(r' [t|T]emp.*?\d+', '', title)
            title = re.sub(r' [c|C]ap.*?\d+', '', title)
        if "audio" in title.lower():        #Reservamos info de audio para después de TMDB
            title_subs += ['[%s]' % scrapertools.find_single_match(title, r'(\[[a|A]udio.*?\])')]
            title = re.sub(r'\[[a|A]udio.*?\]', '', title)
        if "[dual" in title.lower() or "multileng" in title.lower() or "multileng" in item_local.quality.lower():
            item_local.language = "DUAL"
            title = re.sub(r'\[[D|d]ual.*?\]', '', title)
            title = re.sub(r'\[[M|m]ultileng.*?\]', '', title)
            item_local.quality = re.sub(r'\[[M|m]ultileng.*?\]', '', item_local.quality)
        if "duolog" in title.lower():
            title_subs += ["[Saga]"]
            title = title.replace(" Duologia", "").replace(" duologia", "").replace(" Duolog", "").replace(" duolog", "")
        if "trilog" in title.lower():
            title_subs += ["[Saga]"]
            title = title.replace(" Trilogia", "").replace(" trilogia", "").replace(" Trilog", "").replace(" trilog", "")
        if "extendida" in title.lower():
            title_subs += ["[V. Extendida]"]
            title = title.replace(" Version Extendida", "").replace(" (Version Extendida)", "").replace(" V. Extendida", "").replace(" VExtendida", "").replace(" V Extendida", "")
        if "saga" in title.lower():
            title = title.replace(" Saga Completa", "").replace(" saga completa", "").replace(" Saga", "").replace(" saga", "")
            title_subs += ["[Saga]"]
        if "colecc" in title.lower() or "completa" in title.lower():
            title = title.replace(" Coleccion", "").replace(" coleccion", "").replace(" Colecci", "").replace(" colecci", "").replace(" Completa", "").replace(" completa", "").replace(" COMPLETA", "")
            title_subs += ["[Saga]"]
        if scrapertools.find_single_match(title, r'(- [m|M].*?serie ?\w+)'):
            title = re.sub(r'- [m|M].*?serie ?\w+', '', title)
            title_subs += ["[Miniserie]"]

        #Limpiamos restos en título
        title = title.replace("Castellano", "").replace("castellano", "").replace("inglés", "").replace("ingles", "").replace("Inglés", "").replace("Ingles", "").replace("Esp", "").replace("Ing", "").replace("Eng", "").replace("Calidad", "").replace("de la Serie", "")
        
        #Limpiamos cabeceras y colas del título
        if "pelisyseries.com" in host and item_local.contentType == "tvshow":
            title = re.sub(r'Descargar\s', '', title)
        else:
            title = re.sub(r'Descargar\s\w+\s', '', title)
        title = re.sub(r'Descargar\s\w+\-\w+', '', title)
        title = re.sub(r'\(COMPLE.*?\)', '', title)
        title = re.sub(r'\(\d{4}\)$', '', title)
        title = re.sub(r'\d{4}$', '', title)
        title = re.sub(r' \d+x\d+', '', title)
        title = re.sub(r' x\d+', '', title)
        title = title.replace("Ver online ", "").replace("Descarga Serie HD ", "").replace("Descargar Serie HD ", "").replace("Descarga Serie ", "").replace("Ver en linea ", "").replace("Ver en linea", "").replace("HD ", "").replace("(Proper)", "").replace("DVD", "").replace("- ES ", "").replace("ES ", "").replace("COMPLETA", "").strip()
        title = title.replace("Descargar torrent ", "").replace("Descarga Gratis ", "").replace("Descargar Estreno ", "").replace("Pelicula en latino ", "").replace("Descargar Pelicula ", "").replace("Descargar Peliculas ", "").replace("Descargar Todas ", "").replace("Descargar ", "").replace("Descarga ", "").replace("Bajar ", "").replace("RIP ", "").replace("1080p ", "").replace("720p ", "").replace("DVD-Screener ", "").replace("Bonus Disc", "").replace("de Cine ", "").replace("latino", "").replace("Latino", "").replace("argentina", "").replace("Argentina", "").strip()
        
        if "pelisyseries.com" in host and item_local.contentType == "tvshow":
            titulo = ''
            title = title.lower()
            title = re.sub(r'\d+[x|X]\d+', '', title)
            while len(title) > 0:
                palabra = scrapertools.find_single_match(title, r'(^[A-Za-z0-9_.-?ñ]+)')
                if not palabra:
                    break
                title = title.replace(palabra, '')
                title = re.sub(r'^\s+\??', '', title)
                title = re.sub(r'^-\s?', '', title)
                titulo += palabra + " "
                palabra = ""
            title = titulo.title()
        
        if title.endswith("torrent gratis"): title = title[:-15]
        if title.endswith("gratis"): title = title[:-7]
        if title.endswith("torrent"): title = title[:-8]
        if title.endswith("en HD"): title = title[:-6]
        if title.endswith(" -"): title = title[:-2]
        if "en espa" in title: title = title[:-11]
        title = title.replace("a?o", 'año').replace("a?O", 'año').replace("A?o", 'Año').replace("A?O", 'Año')
        while title.endswith(' '):
            title = title[:-1]
        
        #Preparamos calidad
        item_local.quality = item_local.quality.replace("[ ", "").replace(" ]", "")     #Preparamos calidad para Series
        item_local.quality = re.sub(r'\[\d{4}\]', '', item_local.quality)               #Quitar año, si lo tiene
        item_local.quality = re.sub(r'\[Cap.*?\]', '', item_local.quality)              #Quitar episodios, si lo tiene
        item_local.quality = re.sub(r'\[Docu.*?\]', '', item_local.quality)             #Quitar tipo contenidos, si lo tiene
        if "[es-" in item_local.quality.lower() or (("cast" in item_local.quality.lower() or "spani" in item_local.quality.lower()) and ("eng" in item_local.quality.lower() or "ing" in item_local.quality.lower())):     #Mirar si es DUAL
            item_local.language = "DUAL"                                                #Salvar DUAL en idioma
            item_local.quality = re.sub(r'\[[es|ES]-\w+]', '', item_local.quality)      #borrar DUAL
        item_local.quality = re.sub(r'[\s|-][c|C]aste.+', '', item_local.quality)       #Borrar después de Castellano
        item_local.quality = re.sub(r'[\s|-][e|E]spa.+', '', item_local.quality)        #Borrar después de Español
        item_local.quality = re.sub(r'[\s|-|\[][s|S]pani.+', '', item_local.quality)    #Borrar después de Spanish
        item_local.quality = re.sub(r'[\s|-][i|I|e|E]ngl.+', '', item_local.quality)    #Borrar después de Inglés-English
        item_local.quality = item_local.quality.replace("[", "").replace("]", " ").replace("ALTA DEFINICION", "HDTV").replace(" Cap", "")
        #Borrar palabras innecesarias restantes
        item_local.quality = item_local.quality.replace("Espaol", "").replace("Español", "").replace("Espa", "").replace("Castellano ", "").replace("Castellano", "").replace("Spanish", "").replace("English", "").replace("Ingles", "").replace("Latino", "").replace("+Subs", "").replace("-Subs", "").replace("Subs", "").replace("VOSE", "").replace("VOS", "")
        while item_local.quality.endswith(" "):                                         #Borrar espacios de cola
            item_local.quality = item_local.quality[:-1]
        
        #Limpieza final del título y guardado en las variables según su tipo de contenido
        item_local.title = title
        if item_local.contentType == "movie":
            item_local.contentTitle = title
            size = size.replace(".", ",")
            item_local.quality = '%s [%s]' % (item_local.quality, size)
        else:
            item_local.contentSerieName = title
        
        #Guardamos el resto de variables del vídeo
        item_local.url = scrapedurl
        item_local.thumbnail = scrapedthumbnail
        item_local.contentThumbnail = scrapedthumbnail

        #Guardamos el año que puede venir en la url, por si luego no hay resultados desde TMDB
        if year >= "1900" and year <= "2040" and year != "2020":
            title_subs += [year]
        item_local.infoLabels['year'] = '-'
        
        #Guarda la variable temporal que almacena la info adicional del título a ser restaurada después de TMDB
        item_local.title_subs = title_subs

        # Codigo para rescatar lo que se pueda en pelisy.series.com de Series para la Videoteca.  la URL apunta al capítulo y no a la Serie.  Nombre de Serie frecuentemente en blanco. Se obtiene de Thumb, así como el id de la serie
        if ("/serie" in item_local.url or "-serie" in item_local.url) and "pelisyseries.com" in host:
            #Extraer la calidad de la serie basados en la info de la url
            if "seriehd" in url:
                calidad_mps = "series-hd/"
            elif "serievo" in url or "serie-vo" in url:
                calidad_mps = "series-vo/"
            else:
                calidad_mps = "series/"
                
            if "no_image" in scrapedthumbnail:
                real_title_mps = item_local.title
            else:
                real_title_mps = re.sub(r'.*?\/\d+_', '', scrapedthumbnail)
                real_title_mps = re.sub(r'\.\w+.*?', '', real_title_mps)
            
            #Extraer el ID de la serie desde Thumbs (4 dígitos).  Si no hay, nulo
            if "/0_" not in scrapedthumbnail and not "no_image" in scrapedthumbnail:
                serieid = scrapertools.find_single_match(scrapedthumbnail, r'.*?\/\w\/(?P<serieid>\d+).*?.*')
                if len(serieid) > 5:
                    serieid = ""
            else:
                serieid = ""

            #detectar si la url creada de tvshow es válida o hay que volver atras 
            url_id = host + calidad_mps + real_title_mps + "/" + serieid        #A veces necesita el serieid...
            url_tvshow = host + calidad_mps + real_title_mps + "/"              #... otras no.  A probar...
            
            #Leemos la página, a ver  si es una página de episodios
            data_serie = data = re.sub(r"\n|\r|\t|\s{2,}", "", httptools.downloadpage(url_id).data)
            data_serie = unicode(data_serie, "iso-8859-1", errors="replace").encode("utf-8")
            data_serie = data_serie.replace("chapters", "buscar-list")
            
            pattern = '<ul class="%s">(.*?)</ul>' % "buscar-list"       #Patrón de lista de episodios
            if not scrapertools.find_single_match(data_serie, pattern) and serieid:     #no es válida la página, 
                                                                                        #intentarlo con la otra url
                data_serie = data = re.sub(r"\n|\r|\t|\s{2,}", "", httptools.downloadpage(url_tvshow).data)
                data_serie = unicode(data_serie, "iso-8859-1", errors="replace").encode("utf-8")
                data_serie = data_serie.replace("chapters", "buscar-list")
                
                if not scrapertools.find_single_match(data_serie, pattern):     #No ha habido suerte ...
                    item_local.contentType = "movie"                            #tratarlo el capítulo como película
                    item_local.extra = "peliculas"
                else:
                    item_local.url = url_tvshow         #Cambiamos url de episodio por el de serie
            else:
                item_local.url = url_id                 #Cambiamos url de episodio por el de serie

            logger.debug("url: " + item_local.url + " / title o/n: " + item_local.title + " / " + real_title_mps + " / calidad_mps : " + calidad_mps + " / contentType : " + item_local.contentType)
            
            item_local.title = real_title_mps           #Esperemos que el nuevo título esté bien
        
        #Agrega el item local a la lista itemlist
        itemlist.append(item_local.clone())
        
    #Pasamos a TMDB la lista completa Itemlist
    tmdb.set_infoLabels(itemlist, True)
    
    # Pasada para maquillaje de los títulos obtenidos desde TMDB
    for item_local in itemlist:
        title = item_local.title

        #Restauramos la info adicional guarda en la lista title_subs, y la borramos de Item
        if len(item_local.title_subs) > 0:
            title += " "
        for title_subs in item_local.title_subs:
            if "audio" in title_subs.lower():
                title = '%s [%s]' % (title, scrapertools.find_single_match(title_subs, r'[a|A]udio (.*?)'))
                continue
            if scrapertools.find_single_match(title_subs, r'(\d{4})'):
                if not item_local.infoLabels['year'] or item_local.infoLabels['year'] == "-":
                    item_local.infoLabels['year'] = scrapertools.find_single_match(title_subs, r'(\d{4})')
                continue
            if not config.get_setting("unify"):         #Si Titulos Inteligentes NO seleccionados:
                title = '%s %s' % (title, title_subs)
            else:
                title = '%s -%s-' % (title, title_subs)
        del item_local.title_subs
        
        # Si TMDB no ha encontrado el vídeo limpiamos el año
        if item_local.infoLabels['year'] == "-":
            item_local.infoLabels['year'] = ''
            item_local.infoLabels['aired'] = ''
            
        # Preparamos el título para series, con los núm. de temporadas, si las hay
        
        if item_local.contentType == "season" or item_local.contentType == "tvshow":
            item_local.contentTitle= ''
            if item_local.extra == "series":
                title += " -Serie-"
            else:
                title += " -Varios-"

        rating = ''
        if item_local.infoLabels['rating'] and item_local.infoLabels['rating'] != '0.0':
            rating = float(item_local.infoLabels['rating'])
            rating = round(rating, 1)
                
        #Ahora maquillamos un poco los titulos dependiendo de si se han seleccionado títulos inteleigentes o no
        if not config.get_setting("unify"):         #Si Titulos Inteligentes NO seleccionados:
            if item_local.contentType == "season" or item_local.contentType == "tvshow":
                    title = '%s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (title, scrapertools.find_single_match(str(item_local.infoLabels['aired']), r'\/(\d{4})'), rating, item_local.quality, item_local.language)
            
            elif item_local.contentType == "movie":
                title = '%s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (title, str(item_local.infoLabels['year']), rating, item_local.quality, item_local.language)

        if config.get_setting("unify"):         #Si Titulos Inteligentes SÍ seleccionados:
            title = title.replace("[", "-").replace("]", "-")
        
        title = title.replace("--", "").replace(" []", "").replace("()", "").replace("(/)", "").replace("[/]", "")
        title = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', title)
        title = re.sub(r'\s\[COLOR \w+\]\[\/COLOR\]', '', title)
        item_local.title = title
        
        #logger.debug("url: " + item_local.url + " / title: " + item_local.title + " / content title: " + item_local.contentTitle + "/" + item_local.contentSerieName + " / calidad: " + item_local.quality + "[" + item_local.language + "]" + " / calidad ORG: " + calidad + " / year: " + year  + " / tamaño: " + size)

        #logger.debug(item_local)

    if post:
        itemlist.append(item.clone(channel=item.channel, action="listado_busqueda", title="[COLOR gold][B]Pagina siguiente >> [/B][/COLOR]" + str(post_num) + " de " + str(total_pag), thumbnail=get_thumb("next.png"), title_lista=title_lista, cnt_pag=cnt_pag))
                                   
    #logger.debug("Titulos: " + str(len(itemlist)) + " Matches: " + str(len(matches)) + " Post: " + str(item.post) + " / " + str(post_actual) + " / " + str(total_pag))

    return itemlist

def findvideos(item):
    #import xbmc
    logger.info()
    itemlist = []
    
    ## Cualquiera de las tres opciones son válidas
    # item.url = item.url.replace(".com/",".com/ver-online/")
    # item.url = item.url.replace(".com/",".com/descarga-directa/")
    item.url = item.url.replace(".com/", ".com/descarga-torrent/")
    
    # Saber si estamos en una ventana emergente lanzada desde una viñeta del menú principal,
    # con la función "play_from_library"
    #unify_status = False
    #if xbmc.getCondVisibility('Window.IsMedia') == 1:
    #    unify_status = config.get_setting("unify")
    unify_status = config.get_setting("unify")
    
    # Obtener la información actualizada del Episodio, si no la hay
    if not item.infoLabels['tmdb_id'] or (not item.infoLabels['episodio_titulo'] and item.contentType == 'episode'):
        tmdb.set_infoLabels(item, True)
    
    # Descarga la página
    data = re.sub(r"\n|\r|\t|\s{2}|(<!--.*?-->)", "", httptools.downloadpage(item.url).data)
    data = unicode(data, "iso-8859-1", errors="replace").encode("utf-8")
    data = data.replace("$!", "#!").replace("'", "\"").replace("Ã±", "ñ").replace("//pictures", "/pictures")

    #Añadimos el tamaño para todos
    size = scrapertools.find_single_match(data, '<div class="entry-left".*?><a href=".*?span class=.*?>Size:<\/strong>?\s(\d+?\.?\d*?\s\w[b|B])<\/span>')
    size = size.replace(".", ",")       #sustituimos . por , porque Unify lo borra
    item.quality = re.sub('\s\[\d+,?\d*?\s\w[b|B]\]', '', item.quality)     #Quitamos size de calidad, si lo traía
    if size:
        item.title = re.sub('\s\[\d+,?\d*?\s\w[b|B]\]', '', item.title)         #Quitamos size de título, si lo traía
        item.title = '%s [%s]' % (item.title, size)                             #Agregamos size al final del título

    #Limpiamos de año y rating de episodios
    if item.infoLabels['episodio_titulo']:
        item.infoLabels['episodio_titulo'] = re.sub(r'\s?\[.*?\]', '', item.infoLabels['episodio_titulo'])

    #Generamos una copia de Item para trabajar sobre ella
    item_local = item.clone()
    
    # obtenemos la url torrent
    patron = 'class="btn-torrent">.*?window.location.href = "(.*?)";'
    item_local.url = scrapertools.find_single_match(data, patron)
    item_local.url = item_local.url.replace(" ", "%20")             #sustituimos espacios por %20, por si acaso
    #logger.debug("Patron: " + patron + " url: " + item_local.url)
    #logger.debug(data)

    #Pintamos el pseudo-título con toda la información disponible del vídeo
    item_local.action = ""
    item_local.server = "torrent"
    
    rating = ''     #Ponemos el rating
    if item_local.infoLabels['rating'] and item_local.infoLabels['rating'] != '0.0':
        rating = float(item_local.infoLabels['rating'])
        rating = round(rating, 1)
    
    if item_local.contentType == "episode":
        title = '%sx%s' % (str(item_local.contentSeason), str(item_local.contentEpisodeNumber).zfill(2))
        if item_local.infoLabels['temporada_num_episodios']:
            title = '%s (de %s)' % (title, str(item_local.infoLabels['temporada_num_episodios']))
        title = '%s %s' % (title, item_local.infoLabels['episodio_titulo'])
        title_gen = '%s, %s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR] [%s]' % (title, item_local.contentSerieName, item_local.infoLabels['year'], rating, item_local.quality, item_local.language, size)
    else:
        title = item_local.title
        title_gen = title
        
    title_gen = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', title_gen)    #Quitamos etiquetas vacías
    title_gen = re.sub(r'\s\[COLOR \w+\]\[\/COLOR\]', '', title_gen)        #Quitamos colores vacíos
    title_gen = title_gen.replace(" []", "")                                #Quitamos etiquetas vacías
        
    if not unify_status:         #Si Titulos Inteligentes NO seleccionados:
        title_gen = '[COLOR gold]**- Enlaces Ver: [/COLOR]%s [COLOR gold]-**[/COLOR]' % (title_gen)
    else:
        title_gen = '[COLOR gold]Enlaces Ver: [/COLOR]%s' % (title_gen)    

    if config.get_setting("quit_channel_name", "videolibrary") == 1 and item_local.contentChannel == "videolibrary":
        title_gen = '%s: %s' % (item_local.channel.capitalize(), title)

    itemlist.append(item_local.clone(title=title_gen))		#Título con todos los datos del vídeo
    
    #Ahora pintamos el link del Torrent, si lo hay
    if item_local.url:		# Hay Torrent ?
        item_local.title = '[COLOR yellow][?][/COLOR] [COLOR yellow][Torrent][/COLOR] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (item_local.quality, item_local.language)        #Preparamos título de Torrent
        item_local.title = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', item_local.title)  #Quitamos etiquetas vacías
        item_local.title = re.sub(r'\s\[COLOR \w+\]\[\/COLOR\]', '', item_local.title)      #Quitamos colores vacíos
        item_local.alive = "??"         #Calidad del link sin verificar
        item_local.action = "play"      #Visualizar vídeo
        
        itemlist.append(item_local.clone())     #Pintar pantalla
    
    #logger.debug("TORRENT: " + item_local.url + " / title gen/torr: " + title_gen + " / " + title + " / calidad: " + item_local.quality + " / tamaño: " + size + " / content: " + item_local.contentTitle + " / " + item_local.contentSerieName)
    #logger.debug(item_local)

    # VER vídeos, descargar vídeos un link,  o múltiples links
    host_dom = host.replace("https://", "").replace("http://", "").replace("www.", "")
    data = data.replace("http://tumejorserie.com/descargar/url_encript.php?link=", "(")
    data = re.sub(r'javascript:;" onClick="popup\("http:\/\/(?:www.)?' + host_dom + '\w{1,9}\/library\/include\/ajax\/get_modallinks.php\?links=', "", data)

    # Nuevo sistema de scrapeo de servidores creado por Torrentlocula, compatible con otros clones de Newpct1
    patron = '<div class=\"box1\"[^<]+<img src=\"([^<]+)?" style[^<]+><\/div[^<]+<div class="box2">([^<]+)?<\/div[^<]+<div class="box3">([^<]+)?'
    patron += '<\/div[^<]+<div class="box4">([^<]+)?<\/div[^<]+<div class="box5"><a href=(.*?)? rel.*?'
    patron += '<\/div[^<]+<div class="box6">([^<]+)?<'

    enlaces_ver = re.compile(patron, re.DOTALL).findall(data)
    enlaces_descargar = enlaces_ver
    #logger.debug(enlaces_ver)

    #Recorre todos los links de VER
    for logo, servidor, idioma, calidad, enlace, title in enlaces_ver:
        if "ver" in title.lower():
            servidor = servidor.replace("streamin", "streaminto")
            mostrar_server = True
            if config.get_setting("hidepremium"):       #Si no se aceptan servidore premium, se ignoran
                mostrar_server = servertools.is_server_enabled(servidor)
            
            #logger.debug("VER: url: " + enlace + " / title: " + title + " / servidor: " + servidor + " / idioma: " + idioma)

            #Si el servidor es válido, se comprueban si los links están activos
            if mostrar_server:
                try:
                    devuelve = servertools.findvideosbyserver(enlace, servidor)     #activo el link ?
                    if devuelve:
                        enlace = devuelve[0][1]
                        item_local.alive = servertools.check_video_link(enlace, servidor)       #activo el link ?
                        
                        #Si el link no está activo se ignora
                        if item_local.alive == "??":        #dudoso
                            item_local.title = '[COLOR yellow][?][/COLOR] [COLOR yellow][%s][/COLOR] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (servidor.capitalize(), item_local.quality, item_local.language)
                        elif item_local.alive.lower() == "no":      #No está activo.  Lo preparo, pero no lo pinto
                            item_local.title = '[COLOR red][%s][/COLOR] [COLOR yellow][%s][/COLOR] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (item_local.alive, servidor.capitalize(), item_local.quality, item_local.language)
                            logger.debug(item_local.alive + ": ALIVE / " + title + " / " + enlace)
                            raise
                        else:               #Sí está activo
                            item_local.title = '[COLOR yellow][%s][/COLOR] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (servidor.capitalize(), item_local.quality, item_local.language)

                        #Preparamos el resto de variables de Item para ver los vídeos en directo    
                        item_local.action = "play"
                        item_local.server = servidor
                        item_local.url = enlace
                        item_local.title = item_local.title.replace("[]", "")
                        item_local.title = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', item_local.title)
                        item_local.title = re.sub(r'\s\[COLOR \w+\]\[\/COLOR\]', '', item_local.title)
                        itemlist.append(item_local.clone())
                except:
                    pass

    #Ahora vemos los enlaces de DESCARGAR
    if len(enlaces_descargar) > 0:
        
        #Pintamos un pseudo-título de Descargas
        if not unify_status:         #Si Titulos Inteligentes NO seleccionados:
            itemlist.append(item_local.clone(title="[COLOR gold]**- Enlaces Descargar: -**[/COLOR]", action=""))
        else:
            itemlist.append(item_local.clone(title="[COLOR gold] Enlaces Descargar: [/COLOR]", action=""))

    #Recorre todos los links de DESCARGAR
    for logo, servidor, idioma, calidad, enlace, title in enlaces_descargar:
        if "Ver" not in title:
            servidor = servidor.replace("uploaded", "uploadedto")
            partes = enlace.split(" ")      #Partimos el enlace en cada link de las partes
            title = "Descarga"              #Usamos la palabra reservada de Unify para que no formatee el título
            
            #logger.debug("DESCARGAR: url: " + enlace + " / title: " + title + title + " / servidor: " + servidor + " / idioma: " + idioma)
            
            #Recorremos cada una de las partes.  Vemos si el primer link está activo.  Si no lo está ignoramos todo el enlace
            p = 1
            for enlace in partes:
                if not unify_status:         #Si titles Inteligentes NO seleccionados:
                    parte_title = "[COLOR yellow][%s][/COLOR] %s (%s/%s) [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]" % (servidor.capitalize(), title, p, len(partes), item_local.quality, item_local.language)
                else:
                    parte_title = "[COLOR yellow]%s-[/COLOR] %s %s/%s [COLOR limegreen]-%s[/COLOR] [COLOR red]-%s[/COLOR]" % (servidor.capitalize(), title, p, len(partes), item_local.quality, item_local.language)
                p += 1
                mostrar_server = True
                if config.get_setting("hidepremium"):       #Si no se aceptan servidore premium, se ignoran
                    mostrar_server = servertools.is_server_enabled(servidor)
                
                #Si el servidor es válido, se comprueban si los links están activos
                if mostrar_server:
                    try:
                        devuelve = servertools.findvideosbyserver(enlace, servidor)     #activo el link ?
                        if devuelve:
                            enlace = devuelve[0][1]
                            
                            #Verifica si está activo el primer link.  Si no lo está se ignora el enlace-servidor entero
                            if p <= 2:
                                item_local.alive = servertools.check_video_link(enlace, servidor)   #activo el link ?
                                
                                if item_local.alive == "??":        #dudoso
                                    if not unify_status:         #Si titles Inteligentes NO seleccionados:
                                        parte_title = '[COLOR yellow][?][/COLOR] %s' % (parte_title)
                                    else:
                                        parte_title = '[COLOR yellow]%s[/COLOR]-%s' % (item_local.alive, parte_title)
                                elif item_local.alive.lower() == "no":       #No está activo.  Lo preparo, pero no lo pinto
                                    if not unify_status:         #Si titles Inteligentes NO seleccionados:
                                        parte_title = '[COLOR red][%s][/COLOR] %s' % (item_local.alive, parte_title)
                                    else:
                                        parte_title = '[COLOR red]%s[/COLOR]-%s' % (item_local.alive, parte_title)
                                    logger.debug(item_local.alive + ": ALIVE / " + title + " / " + enlace)
                                    break

                            #Preparamos el resto de variables de Item para descargar los vídeos
                            item_local.action = "play"
                            item_local.server = servidor
                            item_local.url = enlace
                            item_local.title = parte_title.replace("[]", "")
                            item_local.title = re.sub(r'\[COLOR \w+\]\[\]\[\/COLOR\]', '', item_local.title)
                            item_local.title = re.sub(r'\[COLOR \w+\]-\[\/COLOR\]', '', item_local.title)
                            itemlist.append(item_local.clone())
                    except:
                        pass
                    
    return itemlist


def episodios(item):
    logger.info()
    itemlist = []

    data = re.sub(r"\n|\r|\t|\s{2,}", "", httptools.downloadpage(item.url).data)
    
    #Busca y pre-carga todas las páginas de episodios que componen las serie, para obtener la url de cada página
    pattern = '<ul class="%s">(.*?)</ul>' % "pagination"  # item.pattern
    pagination = scrapertools.find_single_match(data, pattern)
    if pagination:
        pattern = '<li><a href="([^"]+)">Last<\/a>'     #Busca última página
        full_url = scrapertools.find_single_match(pagination, pattern)
        url, last_page = scrapertools.find_single_match(full_url, r'(.*?\/pg\/)(\d+)')
        list_pages = [item.url]
        for x in range(2, int(last_page) + 1):      #carga cada página para obtener la url de la siguiente
            #LAS SIGUIENTES 3 LINEAS ANULADAS: no es necesario leer la pagína siguiente. Se supone que está activa
            #response = httptools.downloadpage('%s%s'% (url,x))
            #if response.sucess:
            #    list_pages.append("%s%s" % (url, x))    #Guarda la url de la siguiente página en una lista
            list_pages.append("%s%s" % (url, x))    #Guarda la url de la siguiente página en una lista
    else:
        list_pages = [item.url]

    for index, page in enumerate(list_pages):       #Recorre la lista de páginas
        data = re.sub(r"\n|\r|\t|\s{2,}", "", httptools.downloadpage(page).data)
        data = unicode(data, "iso-8859-1", errors="replace").encode("utf-8")
        data = data.replace("chapters", "buscar-list")   #Compatibilidad con mispelisy.series.com
        pattern = '<ul class="%s">(.*?)</ul>' % "buscar-list"  # item.pattern
        if scrapertools.find_single_match(data, pattern):
            data = scrapertools.get_match(data, pattern)
        else:
            logger.debug(item)
            logger.debug("patron: " + pattern + " / data: " + data)
            return itemlist 

        if "pelisyseries.com" in host:
            pattern = '<li[^>]*><div class.*?src="(?P<thumb>[^"]+)?".*?<a class.*?href="(?P<url>[^"]+).*?<h3[^>]+>(?P<info>.*?)?<\/h3>.*?<\/li>'
        else:
            pattern = '<li[^>]*><a href="(?P<url>[^"]+).*?<img.*?src="(?P<thumb>[^"]+)?".*?<h2[^>]+>(?P<info>.*?)?<\/h2>'
        matches = re.compile(pattern, re.DOTALL).findall(data)
        #logger.debug("patron: " + pattern)
        #logger.debug(matches)    
        
        #Empezamos a generar cada episodio
        season = "1"
        for url, thumb, info in matches:
            if "pelisyseries.com" in host:  #En esta web están en diferente orden
                interm = url
                url = thumb
                thumb = interm
            
            item_local = item.clone()       #Creamos copia local de Item por episodio
            item_local.url = url
            item_local.contentThumbnail = thumb
            estado = True                   #Buena calidad de datos por defecto

            if "<span" in info:  # new style
                pattern = ".*?[^>]+>.*?Temporada\s*(?P<season>\d+)?.*?Capitulo(?:s)?\s*(?P<episode>\d+)?" \
                          "(?:.*?(?P<episode2>\d+)?)<.+?<span[^>]+>(?P<lang>.*?)?<\/span>\s*Calidad\s*<span[^>]+>" \
                          "[\[]\s*(?P<quality>.*?)?\s*[\]]<\/span>"
                if "Especial" in info: # Capitulos Especiales
                    pattern = ".*?[^>]+>.*?Temporada.*?\[.*?(?P<season>\d+).*?\].*?Capitulo.*?\[\s*(?P<episode>\d+).*?\]?(?:.*?(?P<episode2>\d+)?)<.+?<span[^>]+>(?P<lang>.*?)?<\/span>\s*Calidad\s*<span[^>]+>[\[]\s*(?P<quality>.*?)?\s*[\]]<\/span>"
                
                if not scrapertools.find_single_match(info, pattern):   #en caso de error de formato, creo uno básico
                    logger.debug("patron episodioNEW: " + pattern)
                    logger.debug(info)
                    logger.debug(item_local.url)
                    info = '><strong>%sTemporada %s Capitulo 0</strong> - <span >Español Castellano</span> Calidad <span >[%s]</span>' % (item_local.contentSerieName, season, item_local.quality)

            else:  # old style.  Se intenta buscar un patrón que encaje con los diversos formatos antiguos.  Si no, se crea
                pattern = '\[(?P<quality>.*?)\]\[Cap.(?P<season>\d).*?(?P<episode>\d{2})(?:_(?P<season2>\d+)(?P<episode2>\d{2}))?\].*?(?P<lang>.*)?'        #Patrón básico por defecto

                if scrapertools.find_single_match(info, '\[\d{3}\]'):
                    info = re.sub(r'\[(\d{3}\])', r'[Cap.\1', info)
                elif scrapertools.find_single_match(info, '\[Cap.\d{2}_\d{2}\]'):
                    info = re.sub(r'\[Cap.(\d{2})_(\d{2})\]', r'[Cap.1\1_1\2]', info)
                elif scrapertools.find_single_match(info, '\[Cap.([A-Za-z]+)\]'):
                    info = re.sub(r'\[Cap.([A-Za-z]+)\]', '[Cap.100]', info)
                if scrapertools.find_single_match(info, '\[Cap.\d{2,3}'):
                    pattern = "\[(?P<quality>.*?)\].*?\[Cap.(?P<season>\d).*?(?P<episode>\d{2})(?:_(?P<season2>\d+)" \
                          "(?P<episode2>\d{2}))?.*?\].*?(?:\[(?P<lang>.*?)\])?"
                elif scrapertools.find_single_match(info, 'Cap.\d{2,3}'):
                    pattern = ".*?Temp.*?\s(?P<quality>.*?)\s.*?Cap.(?P<season>\d).*?(?P<episode>\d{2})(?:_(?P<season2>\d+)(?P<episode2>\d{2}))?.*?\s(?P<lang>.*)?"
                elif scrapertools.find_single_match(info, '(?P<quality>.*?)?(?P<season>\d)[x|X|\.](?P<episode>\d{2})\s?(?:_(?P<season2>\d+)(?P<episode2>\d{2}))?.*?(?P<lang>.*)?'):
                    pattern = "(?P<quality>.*?)?(?P<season>\d)[x|X|\.](?P<episode>\d{2})\s?(?:_(?P<season2>\d+)(?P<episode2>\d{2}))?.*?(?P<lang>.*)?"
                    estado = False      #Mala calidad de datos
                if not scrapertools.find_single_match(info, pattern):   #en caso de error de formato, creo uno básico
                    logger.debug("patron episodioOLD: " + pattern)
                    logger.debug(info)
                    logger.debug(item_local.url)
                    info = '%s - Temp.%s [%s][Cap.%s00][Spanish]' % (item_local.contentSerieName, season, item_local.quality, season)
                    estado = False      #Mala calidad de datos
            
            r = re.compile(pattern)
            match = [m.groupdict() for m in r.finditer(info)][0]

            if match['season'] is None: match['season'] = season    #Si no se encuentran valores, pero poner lo básico
            if match['episode'] is None: match['episode'] = "0"
                    
            if match['quality'] and not item_local.quality and estado == True:
                item_local.quality = match['quality']       #Si hay quality se coge, si no, la de la serie
                item_local.quality = item_local.quality.replace("ALTA DEFINICION", "HDTV")
            
            if match['lang'] and estado == False:
                item_local.infoLabels['episodio_titulo'] = match['lang']

            if match["episode2"]:       #Hay episodio dos? es una entrada múltiple?
                item_local.title = "%sx%s al %s -" % (str(match["season"]), str(match["episode"]).zfill(2), str(match["episode2"]).zfill(2))            #Creamos un título con el rango de episodios
            else:                   #Si es un solo episodio, se formatea ya
                item_local.title = "%sx%s -" % (match["season"], str(match["episode"]).zfill(2))

            item_local.contentEpisodeNumber = match['episode']
            item_local.contentSeason = match['season']
            item_local.action = "findvideos"
            item_local.extra = "episodios"
            
            itemlist.append(item_local.clone())
                            
            #logger.debug("title: " + item_local.title + " / url: " + item_local.url + " / calidad: " + item_local.quality + " / Season: " + str(item_local.contentSeason) + " / EpisodeNumber: " + str(item_local.contentEpisodeNumber))
    
    # Pasada por TMDB y clasificación de lista por temporada y episodio
    tmdb.set_infoLabels(itemlist, seekTmdb = True)
    if len(itemlist) > 1:
        itemlist = sorted(itemlist, key=lambda it: (int(it.contentSeason), int(it.contentEpisodeNumber)))

    # Pasada para maqullaje de los títulos obtenidos desde TMDB
    for item_local in itemlist:
        
        # Si no hay datos de TMDB, pongo los datos locales que conozco
        if item_local.infoLabels['aired']:
            item_local.infoLabels['year'] = scrapertools.find_single_match(str(item_local.infoLabels['aired']), r'\/(\d{4})')
        
        rating = ''
        if item_local.infoLabels['rating'] and item_local.infoLabels['rating'] != '0.0':
            rating = float(item_local.infoLabels['rating'])
            rating = round(rating, 1)
            
        #Preparamos el título para que sea compatible con Añadir Serie a Videoteca
        if item_local.infoLabels['episodio_titulo']:
            if "al" in item_local.title:        #Si son episodios múltiples, ponemos nombre de serie
                item_local.title = '%s %s' % (item_local.title, item_local.contentSerieName)
                item_local.infoLabels['episodio_titulo'] = '%s %s' % (scrapertools.find_single_match(item_local.title, r'(al \d+)'), item_local.contentSerieName)
            else:
                item_local.title = '%s %s' % (item_local.title, item_local.infoLabels['episodio_titulo'])
            if item_local.infoLabels['year']:
                item_local.infoLabels['episodio_titulo'] = '%s [%s]' % (item_local.infoLabels['episodio_titulo'], item_local.infoLabels['year'])
            if rating:
                item_local.infoLabels['episodio_titulo'] = '%s [%s]' % (item_local.infoLabels['episodio_titulo'], rating)
        else:
            item_local.title = '%s %s' % (item_local.title, item_local.contentSerieName)
        item_local.title = '%s [COLOR yellow][%s][/COLOR] [%s] [COLOR limegreen][%s][/COLOR] [COLOR red][%s][/COLOR]' % (item_local.title, item_local.infoLabels['year'], rating, item_local.quality, item_local.language)
        
        #Quitamos campos vacíos
        item_local.infoLabels['episodio_titulo'] = item_local.infoLabels['episodio_titulo'].replace(" []", "")
        item_local.title = item_local.title.replace(" []", "")
        item_local.title = re.sub(r'\s\[COLOR \w+\]\[\]\[\/COLOR\]', '', item_local.title)
        item_local.title = re.sub(r'\s\[COLOR \w+\]-\[\/COLOR\]', '', item_local.title)
        
        #logger.debug("title=[" + item_local.title + "], url=[" + item_local.url + "], item=[" + str(item_local) + "]")
    
    if config.get_videolibrary_support() and len(itemlist) > 0:
        title = ''
        if item_local.infoLabels['temporada_num_episodios']:
            title = ' [Temp. de %s ep.]' % item_local.infoLabels['temporada_num_episodios']
            
        itemlist.append(item.clone(title="[COLOR yellow]Añadir esta serie a la videoteca[/COLOR]" + title, action="add_serie_to_library", extra="episodios"))

    return itemlist

def search(item, texto):
    logger.info("search:" + texto)
    # texto = texto.replace(" ", "+")

    try:
        item.post = "q=%s" % texto
        item.pattern = "buscar-list"
        itemlist = listado_busqueda(item)
        
        return itemlist

    # Se captura la excepción, para no interrumpir al buscador global si un canal falla
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []

def newest(categoria):
    logger.info()
    itemlist = []
    item = Item()
    try:
        item.extra = 'pelilist'
        if categoria == 'torrent':
            item.url = host+'peliculas/'

            itemlist = listado(item)
            if itemlist[-1].title == ">> Página siguiente":
                itemlist.pop()
            item.url = host+'series/'
            itemlist.extend(listado(item))
            if itemlist[-1].title == ">> Página siguiente":
                itemlist.pop()
                
        if categoria == 'peliculas 4k':
            item.url = host+'peliculas-hd/4kultrahd/'
            itemlist.extend(listado(item))
            if itemlist[-1].title == ">> Página siguiente":
                 itemlist.pop()
                
        if categoria == 'anime':
            item.url = host+'anime/'
            itemlist.extend(listado(item))
            if itemlist[-1].title == ">> Página siguiente":
                 itemlist.pop()
                                 
        if categoria == 'documentales':
            item.url = host+'documentales/'
            itemlist.extend(listado(item))
            if itemlist[-1].title == ">> Página siguiente":
                itemlist.pop()

    # Se captura la excepción, para no interrumpir al canal novedades si un canal falla
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []

    return itemlist
