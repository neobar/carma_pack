__author__ = 'brandonkelly'

import numpy as np
import carmcmc as cm
import matplotlib.pyplot as plt
import multiprocessing as mp
from os import environ
import pickle
from scipy.misc import comb
from astropy.io import fits


base_dir = environ['HOME'] + '/Projects/carma_pack/src/paper/'
data_dir = base_dir + 'data/'

def make_sampler_plots(time, y, ysig, pmax, file_root, title, do_mags=False):

    froot = base_dir + 'plots/' + file_root

    print 'Getting maximum-likelihood estimates...'

    carma_model = cm.CarmaModel(time, y, ysig)
    MAP, pqlist, AIC_list = carma_model.choose_order(pmax, njobs=-1)

    # convert lists to a numpy arrays, easier to manipulate
    pqarray = np.array(pqlist)
    pmodels = pqarray[:, 0]
    qmodels = pqarray[:, 1]
    AICc = np.array(AIC_list)

    plt.clf()
    plt.subplot(111)
    for i in xrange(qmodels.max()+1):
        plt.plot(pmodels[qmodels == i], AICc[qmodels == i], 's-', label='q=' + str(i), lw=2)
    plt.legend(loc=9)
    plt.xlabel('p')
    plt.ylabel('AICc(p,q)')
    plt.xlim(0, pmodels.max() + 1)
    plt.title(title)
    plt.savefig(froot + 'aic.eps')
    plt.close()

    nsamples = 50000
    carma_sample = carma_model.run_mcmc(nsamples)
    carma_sample.add_map(MAP)

    ax = plt.subplot(111)
    print 'Getting bounds on PSD...'
    psd_low, psd_hi, psd_mid, frequencies = carma_sample.plot_power_spectrum(percentile=95.0, sp=ax, doShow=False,
                                                                             color='SkyBlue', nsamples=5000)
    psd_mle = cm.power_spectrum(frequencies, carma_sample.map['sigma'], carma_sample.map['ar_coefs'],
                                ma_coefs=np.atleast_1d(carma_sample.map['ma_coefs']))
    ax.loglog(frequencies, psd_mle, '--b', lw=2)
    noise_level = np.mean(ysig ** 2)
    ax.loglog(frequencies, np.ones(frequencies.size) * noise_level, color='grey', lw=2)
    ax.set_ylim(bottom=noise_level / 100.0)
    ax.annotate("Measurement Noise Level", (3.0 * ax.get_xlim()[0], noise_level / 2.5))
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Power Spectral Density')
    plt.title(title)
    plt.savefig(froot + 'psd.eps')

    print 'Assessing the fit quality...'
    fig = carma_sample.assess_fit(doShow=False)
    ax_again = fig.add_subplot(2, 2, 1)
    ax_again.set_title(title)
    if do_mags:
        ylims = ax_again.get_ylim()
        ax_again.set_ylim(ylims[1], ylims[0])
        ax_again.set_ylabel('magnitude')
    else:
        ax_again.set_ylabel('Flux')
    plt.savefig(froot + 'fit_quality.eps')

    return carma_sample


def do_simulated_regular():

    # first generate some data assuming a CARMA(5,3) process on a uniform grid
    sigmay = 2.3  # dispersion in lightcurve
    p = 5  # order of AR polynomial
    qpo_width = np.array([1.0/100.0, 1.0/100.0, 1.0/500.0])
    qpo_cent = np.array([1.0/5.0, 1.0/50.0])
    ar_roots = cm.get_ar_roots(qpo_width, qpo_cent)
    ma_coefs = np.zeros(p)
    ma_coefs[0] = 1.0
    ma_coefs[1] = 4.5
    ma_coefs[2] = 1.25
    sigsqr = sigmay ** 2 / cm.carma_variance(1.0, ar_roots, ma_coefs=ma_coefs)

    ny = 1028
    time = np.arange(0.0, ny)
    y0 = cm.carma_process(time, sigsqr, ar_roots, ma_coefs=ma_coefs)

    ysig = np.ones(ny) * np.sqrt(1e-2)
    # ysig = np.ones(ny) * np.sqrt(1e-6)

    y = y0 + ysig * np.random.standard_normal(ny)

    froot = base_dir + 'plots/car5_regular_'

    plt.subplot(111)
    plt.plot(time, y0, 'k-')
    plt.plot(time, y, '.')
    plt.xlim(time.min(), time.max())
    plt.xlabel('Time')
    plt.ylabel('CARMA(5,3) Process')
    plt.savefig(froot + 'tseries.eps')

    ar_coef = np.poly(ar_roots)

    print 'Getting maximum-likelihood estimates...'

    carma_model = cm.CarmaModel(time, y, ysig)
    pmax = 7
    MAP, pqlist, AIC_list = carma_model.choose_order(pmax, njobs=-1)

    # convert lists to a numpy arrays, easier to manipulate
    pqarray = np.array(pqlist)
    pmodels = pqarray[:, 0]
    qmodels = pqarray[:, 1]
    AICc = np.array(AIC_list)

    plt.clf()
    plt.subplot(111)
    for i in xrange(qmodels.max()+1):
        plt.plot(pmodels[qmodels == i], AICc[qmodels == i], 's-', label='q=' + str(i), lw=2)
    plt.legend()
    plt.xlabel('p')
    plt.ylabel('AICc(p,q)')
    plt.xlim(0, pmodels.max() + 1)
    plt.savefig(froot + 'aic.eps')
    plt.close()

    nsamples = 50000
    carma_sample = carma_model.run_mcmc(nsamples)
    carma_sample.add_map(MAP)

    plt.subplot(111)
    pgram, freq = plt.psd(y)
    plt.clf()

    ax = plt.subplot(111)
    print 'Getting bounds on PSD...'
    psd_low, psd_hi, psd_mid, frequencies = carma_sample.plot_power_spectrum(percentile=95.0, sp=ax, doShow=False,
                                                                             color='SkyBlue', nsamples=5000)
    psd_mle = cm.power_spectrum(frequencies, carma_sample.map['sigma'], carma_sample.map['ar_coefs'],
                                ma_coefs=np.atleast_1d(carma_sample.map['ma_coefs']))
    ax.loglog(freq / 2.0, pgram, 'o', color='DarkOrange')
    psd = cm.power_spectrum(frequencies, np.sqrt(sigsqr), ar_coef, ma_coefs=ma_coefs)
    ax.loglog(frequencies, psd, 'k', lw=2)
    ax.loglog(frequencies, psd_mle, '--b', lw=2)
    noise_level = np.mean(ysig ** 2)
    ax.loglog(frequencies, np.ones(frequencies.size) * noise_level, color='grey', lw=2)
    ax.set_ylim(bottom=noise_level / 100.0)
    ax.annotate("Measurement Noise Level", (3.0 * ax.get_xlim()[0], noise_level / 2.5))
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Power Spectral Density')

    plt.savefig(froot + 'psd.eps')

    print 'Assessing the fit quality...'
    carma_sample.assess_fit(doShow=False)
    plt.savefig(froot + 'fit_quality.eps')


def do_simulated_irregular():

    # first generate some data assuming a CARMA(5,3) process on a uniform grid
    sigmay = 2.3  # dispersion in lightcurve
    p = 5  # order of AR polynomial
    mu = 17.0  # mean of time series
    qpo_width = np.array([1.0/100.0, 1.0/300.0, 1.0/200.0])
    qpo_cent = np.array([1.0/5.0, 1.0/25.0])
    ar_roots = cm.get_ar_roots(qpo_width, qpo_cent)
    ma_coefs = np.zeros(p)
    ma_coefs[0] = 1.0
    ma_coefs[1] = 4.5
    ma_coefs[2] = 1.25
    sigsqr = sigmay ** 2 / cm.carma_variance(1.0, ar_roots, ma_coefs=ma_coefs)

    ny = 270
    time = np.empty(ny)
    dt = np.random.uniform(1.0, 3.0, ny)
    time[0:90] = np.cumsum(dt[0:90])
    time[90:2*90] = 180 + time[90-1] + np.cumsum(dt[90:2*90])
    time[2*90:] = 180 + time[2*90-1] + np.cumsum(dt[2*90:])

    y = mu + cm.carma_process(time, sigsqr, ar_roots, ma_coefs=ma_coefs)

    ysig = np.ones(ny) * y.std() / 5.0
    # ysig = np.ones(ny) * 1e-6
    y0 = y.copy()
    y += ysig * np.random.standard_normal(ny)

    data = (time, y, ysig)

    froot = base_dir + 'plots/car5_irregular_'

    plt.subplot(111)
    for i in xrange(3):
        plt.plot(time[90*i:90*(i+1)], y0[90*i:90*(i+1)], 'k', lw=2)
        plt.plot(time[90*i:90*(i+1)], y[90*i:90*(i+1)], 'bo')

    plt.xlim(time.min(), time.max())
    plt.xlabel('Time')
    plt.ylabel('CARMA(5,3) Process')
    plt.savefig(froot + 'tseries.eps')

    ar_coef = np.poly(ar_roots)

    print 'Getting maximum-likelihood estimates...'

    carma_model = cm.CarmaModel(time, y, ysig)
    pmax = 7
    MAP, pqlist, AIC_list = carma_model.choose_order(pmax, njobs=-1)

    # convert lists to a numpy arrays, easier to manipulate
    pqarray = np.array(pqlist)
    pmodels = pqarray[:, 0]
    qmodels = pqarray[:, 1]
    AICc = np.array(AIC_list)

    plt.clf()
    plt.subplot(111)
    for i in xrange(qmodels.max()+1):
        plt.plot(pmodels[qmodels == i], AICc[qmodels == i], 's-', label='q=' + str(i), lw=2)
    plt.legend()
    plt.xlabel('p')
    plt.ylabel('AICc(p,q)')
    plt.xlim(0, pmodels.max() + 1)
    plt.savefig(froot + 'aic.eps')
    plt.close()

    nsamples = 50000
    carma_sample = carma_model.run_mcmc(nsamples)
    carma_sample.add_map(MAP)

    plt.clf()
    ax = plt.subplot(111)
    print 'Getting bounds on PSD...'
    psd_low, psd_hi, psd_mid, frequencies = carma_sample.plot_power_spectrum(percentile=95.0, sp=ax, doShow=False,
                                                                             color='SkyBlue', nsamples=5000)
    psd_mle = cm.power_spectrum(frequencies, carma_sample.map['sigma'], carma_sample.map['ar_coefs'],
                                ma_coefs=np.atleast_1d(carma_sample.map['ma_coefs']))
    psd = cm.power_spectrum(frequencies, np.sqrt(sigsqr), ar_coef, ma_coefs=ma_coefs)
    ax.loglog(frequencies, psd_mle, '--b', lw=2)
    ax.loglog(frequencies, psd, 'k', lw=2)
    noise_level = np.mean(ysig ** 2) * dt.min()
    ax.loglog(frequencies, np.ones(frequencies.size) * noise_level, color='grey', lw=2)
    ax.set_ylim(bottom=noise_level / 100.0)
    ax.annotate("Measurement Noise Level", (3.0 * ax.get_xlim()[0], noise_level / 2.5))
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Power Spectral Density')

    plt.savefig(froot + 'psd.eps')

    print 'Assessing the fit quality...'
    carma_sample.assess_fit(doShow=False)
    plt.savefig(froot + 'fit_quality.eps')

    # compute the marginal mean and variance of the predicted values
    nplot = 1028
    time_predict = np.linspace(time.min(), 1.25 * time.max(), nplot)
    time_predict = time_predict[1:]
    predicted_mean, predicted_var = carma_sample.predict_lightcurve(time_predict, bestfit='map')
    predicted_low = predicted_mean - np.sqrt(predicted_var)
    predicted_high = predicted_mean + np.sqrt(predicted_var)

    # plot the time series and the marginal 1-sigma error bands
    plt.clf()
    plt.subplot(111)
    plt.fill_between(time_predict, predicted_low, predicted_high, color='cyan')
    plt.plot(time_predict, predicted_mean, '-b', label='Predicted')
    plt.plot(time[0:90], y0[0:90], 'k', lw=2, label='True')
    plt.plot(time[0:90], y[0:90], 'bo')
    for i in xrange(1, 3):
        plt.plot(time[90*i:90*(i+1)], y0[90*i:90*(i+1)], 'k', lw=2)
        plt.plot(time[90*i:90*(i+1)], y[90*i:90*(i+1)], 'bo')

    plt.xlabel('Time')
    plt.ylabel('CARMA(5,3) Process')
    plt.xlim(time_predict.min(), time_predict.max())
    plt.legend()
    plt.savefig(froot + 'interp.eps')


def do_AGN_Stripe82():

    s82_id = '1627677'
    data = np.genfromtxt(data_dir + s82_id)
    # do r-band data
    jdate = data[:, 6]
    rmag = data[:, 7]
    rerr = data[:, 8]

    carma_sample = make_sampler_plots(jdate - jdate.min(), rmag, rerr, 7, s82_id + '_', 'S82 Quasar, r-band',
                                      do_mags=True)


def do_AGN_Kepler():

    sname = 'Zw 229-15'
    data = fits.open(data_dir + 'zw229_long2.fits')[1].data
    jdate = data['time']
    flux = data['SAP_FLUX']
    ferr = data['SAP_FLUX_ERR']

    keep = np.isfinite(jdate)
    jdate = jdate[keep]
    jdate -= jdate.min()
    flux = flux[keep]
    ferr = ferr[keep]
    carma_sample = make_sampler_plots(jdate, flux, ferr, 9, 'zw229_', sname)

    # transform the flux through end matching
    tflux = flux - flux[0]
    slope = (tflux[-1] - tflux[0]) / (jdate[-1] - jdate[0])
    tflux -= slope * jdate

    plt.subplot(111)
    pgram, freq = plt.psd(tflux, NFFT=512)
    plt.clf()

    ax = plt.subplot(111)
    print 'Getting bounds on PSD...'
    psd_low, psd_hi, psd_mid, frequencies = carma_sample.plot_power_spectrum(percentile=95.0, sp=ax, doShow=False,
                                                                             color='SkyBlue', nsamples=5000)
    psd_mle = cm.power_spectrum(frequencies, carma_sample.map['sigma'], carma_sample.map['ar_coefs'],
                                ma_coefs=np.atleast_1d(carma_sample.map['ma_coefs']))
    ax.loglog(freq / 2.0, pgram, 'o', color='DarkOrange')
    ax.loglog(frequencies, psd_mle, '--b', lw=2)
    noise_level = np.mean(ferr ** 2)
    ax.loglog(frequencies, np.ones(frequencies.size) * noise_level, color='grey', lw=2)
    ax.set_ylim(bottom=noise_level / 100.0)
    ax.annotate("Measurement Noise Level", (3.0 * ax.get_xlim()[0], noise_level / 2.5))
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Power Spectral Density')

    plt.savefig(base_dir + 'plots/zw229_psd.eps')

    plt.clf()
    carma_sample.plot_1dpdf('measerr_scale')
    plt.savefig(base_dir + 'plots/zw229_measerr_scale.eps')
    measerr_scale = carma_sample.get_samples('measerr_scale')
    print "95% credibility interval on Kepler measurement error scale parameter:", np.percentile(measerr_scale, 2.5), \
        np.percentile(measerr_scale, 97.5)


def do_AGN_Xray():

    sname = 'MCG-6-30-15'
    data = np.genfromtxt(data_dir + 'lcurve_rxte_xmm.dat')
    jdate = data[:, 0]
    flux = data[:, 1]
    ferr = data[:, 2]

    carma_sample = make_sampler_plots(jdate - jdate.min(), flux, ferr, 9, 'mcg63015_', sname)


def do_RRLyrae():

    dtype = np.dtype([("mjd", np.float), ("filt", np.str, 1), ("mag", np.float), ("dmag", np.float)])
    data = np.loadtxt(data_dir + 'RRLyrae.txt', comments="#", dtype=dtype)

    # do g-band light curve
    gIdx = np.where(data["filt"] == "g")
    jdate = data['mjd'][gIdx]
    gmag = data['mag'][gIdx]
    gerr = data['dmag'][gIdx]

    carma_sample = make_sampler_plots(jdate - jdate.min(), gmag, gerr, 7, 'RRLyrae_', 'RR Lyrae, g-band', do_mags=True)


def do_OGLE_LPV():
    pass


def compare_LPV_QSO():
    pass




if __name__ == "__main__":
    do_simulated_regular()
    do_simulated_irregular()
    # do_AGN_Stripe82()
    do_AGN_Kepler()