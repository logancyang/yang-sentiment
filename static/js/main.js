
function getTweetStream() {
  let source = new EventSource("/latest_tweets");
  source.onmessage = function (event) {
    tweet_list = JSON.parse(event.data)
    $('blockquote#tweet-1').text(tweet_list[4]);
    $('blockquote#tweet-2').text(tweet_list[3]);
    $('blockquote#tweet-3').text(tweet_list[2]);
    $('blockquote#tweet-4').text(tweet_list[1]);
    $('blockquote#tweet-5').text(tweet_list[0]);
  }
}

function getYangTweetCount() {
  let source = new EventSource("/yangcount");
  source.onmessage = function (event) {
    $('div.yang-count').text(event.data);
  }
}


/* Chart building */

function getColor(colorKey) {
  colorSets = {
    'red': {
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      borderColor: 'rgba(255, 99, 132, 1)'
    },
    'blue': {
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      borderColor: 'rgba(54, 162, 235, 1)'
    },
    'yellow': {
      backgroundColor: 'rgba(255, 206, 86, 0.2)',
      borderColor: 'rgba(255, 206, 86, 1)'
    },
    'green': {
      backgroundColor: 'rgba(75, 192, 192, 0.2)',
      borderColor: 'rgba(75, 192, 192, 1)'
    },
    'purple': {
      backgroundColor: 'rgba(153, 102, 255, 0.2)',
      borderColor: 'rgba(153, 102, 255, 1)'
    },
    'orange': {
      backgroundColor: 'rgba(255, 159, 64, 0.2)',
      borderColor: 'rgba(255, 159, 64, 1)'
    }
  }
  return colorSets[colorKey]
}

function _getxValues(data, xTickType, lastExclusive) {
  const xValues = []
  let data_trimmed = data
  if (lastExclusive) {
    data_trimmed = data.slice(0, data.length - 1)
  }
  for (const timestamp of data_trimmed) {
    let xTick = new Date(timestamp * 1000)
    x = _getTimeTick(xTick, xTickType)
    xValues.push(x)
  }
  return xValues
}

function _getyValues(data, lastExclusive) {
  return lastExclusive ? data : data.slice(0, data.length - 1)
}

function _getTimeTick(xTick, xTickType) {
  if (xTickType === 'minute') {
    const minuteOptions = {
      timeZone: 'America/New_York',
      hour: 'numeric',
      minute: 'numeric'
    }
    return xTick.toLocaleTimeString('en-US', minuteOptions)
  } else if (xTickType === 'day') {
    const dayOptions = {
      weekday: 'short',
      timeZone: 'America/New_York',
      month: 'numeric',
      day: 'numeric'
    }
    return xTick.toLocaleDateString('en-US', dayOptions)
  }
}

function _getMinMaxYValue(datasets) {
  // Asume there is only one dataset (no multi-line chart)
  const data = datasets[0].data
  return {
    minyValue: Math.min(...data),
    maxyValue: Math.max(...data, 0)
  };
}

/**
 * Takes an array of objects from the server in form {label, data}
 * and turn into an array of {label, data, backgroundColor, borderColor, borderWidth}
 * @param {array} chartData chartData.data here is
 * {
 *   timestamps: [x, x, x, ...],
 *   counts: [y, y, ...],
 *   trendline: [y, y, y, ...],
 *   trend: true / false
 * }
 * @param {string} xTickType Can be 'minute' or 'day'
 */
function fillChartDatasets(chartData, colors, xTickType, lastExclusive) {
  datasets = []
  let xlabels = []
  let colorInd = 0
  /* key is timestamps, counts, trendline, trend
  */
  for (const [key, chartDatum] of Object.entries(chartData.data)) {
    if (key === 'trend') {
      continue
    }
    if (key === 'timestamps') {
      xlabels = _getxValues(chartDatum, xTickType, lastExclusive = lastExclusive)
      continue
    }
    let fill = true
    if (key === 'trendline') {
      fill = false
    }

    const { backgroundColor, borderColor } = getColor(colors[colorInd])
    colorInd += 1
    const yValues = _getyValues(chartDatum, lastExclusive = lastExclusive)

    datum = {
      label: key,
      data: yValues,
      backgroundColor,
      borderColor,
      borderWidth: 1,
      fill
    }
    datasets.push(datum)
  }
  return {
    xlabels,
    datasets
  }
}

function renderCharts(
  chartId, chartData, colors, chartType = 'bar', xTickType = 'minute', lastExclusive = true) {
  let ctx = document.getElementById(chartId).getContext('2d');
  const { xlabels, datasets } = fillChartDatasets(
    chartData, colors, xTickType, lastExclusive = lastExclusive)
  const {minyValue, maxyValue} = _getMinMaxYValue(datasets)
  let chart = new Chart(ctx, {
    type: chartType,
    data: {
      labels: xlabels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      title: {
        display: true,
        text: chartData.title
      },
      elements: {
        point: {
          radius: 0
        }
      },
      scales: {
        yAxes: [{
          ticks: {
            suggestedMin: minyValue * 0.95,
            suggestedMax: maxyValue * 1.05
          }
        }]
      }
    }
  });
  return chart
}

async function renderChartOnDemand(chartOptions) {
  const {
    chartId, spinnerId, endpoint, chartType,
    title, color, xTickType, lastExclusive
  } = chartOptions

  let response = await fetch(`/${endpoint}`);
  let chartDataRaw = await response.json()
  const chartData = {
    data: chartDataRaw,
    title
  }
  const trendColor = chartDataRaw.trend ? 'green' : 'red'
  const loadingSpinner = document.getElementById(spinnerId);
  if (loadingSpinner) {
    loadingSpinner.parentNode.removeChild(loadingSpinner);
  }
  return renderCharts(
    chartId,
    chartData,
    colors = [color, trendColor],
    chartType,
    xTickType,
    lastExclusive
  )
}

function getLiveInfo() {
  getYangTweetCount()
  getTweetStream()

  // Charts
  const yangMChart = renderChartOnDemand({
    chartId: "yang-minute-count-line",
    spinnerId: "yang-minute-loading",
    endpoint: "tweets_min_chart",
    chartType: "line",
    title: "# yang tweets in the last 6hr",
    color: 'blue',
    xTickType: 'minute',
    lastExclusive: true
  })

  const yangDChart = renderChartOnDemand({
    chartId: "yang-day-count-line",
    spinnerId: "yang-day-loading",
    endpoint: "tweets_daily_chart",
    chartType: "line",
    title: "# yang tweets in the last 2 weeks",
    color: 'yellow',
    xTickType: 'day',
    lastExclusive: true
  })

  // renderCharts('day-count-line', chartData=myChartData, colors=['blue', 'yellow'])
  // renderCharts('loc-count-hist', chartData=myChartData, colors=['purple', 'orange'])
  // renderCharts('loc1-count-hist', chartData=myChartData, colors=['blue', 'yellow'])
}

window.onload = getLiveInfo
